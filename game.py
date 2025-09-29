import pygame
import sys
import math

pygame.init()
pygame.mixer.init()
# -------------------------
# Screen setup
# -------------------------
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Clocked In")
clock = pygame.time.Clock()

pygame.mixer.music.load("ClockedIn-Theme.mp3")
pygame.mixer.music.set_volume(0.7)
pygame.mixer.music.play(-1)
# -------------------------
# World size
# -------------------------
WORLD_WIDTH, WORLD_HEIGHT = 2400, 1200
background_present = pygame.image.load("sunset.png").convert()
background_past = pygame.image.load("sunrise.png").convert()

# Scale to fit screen size (if needed)
background_present = pygame.transform.scale(background_present, (WIDTH, HEIGHT))
background_past = pygame.transform.scale(background_past, (WIDTH, HEIGHT))

# -------------------------
# Laser class (from earlier)
# -------------------------
class Laser:
    def __init__(self, rect, axis='h', off_duration=2000, warning_duration=1500, on_duration=2500, active_in_timelines=('present',), start_offset=0):
        self.rect = rect.copy()
        self.axis = axis
        self.off_duration = off_duration
        self.warning_duration = warning_duration
        self.on_duration = on_duration
        self.cycle_length = off_duration + warning_duration + on_duration
        self.active_in_timelines = tuple(active_in_timelines)
        self.start_time = pygame.time.get_ticks() + start_offset

    def state_at(self, now_ms):
        t = (now_ms - self.start_time) % self.cycle_length
        if t < self.off_duration:
            return 'off', t
        t -= self.off_duration
        if t < self.warning_duration:
            return 'warning', t
        t -= self.warning_duration
        return 'on', t

    def update_and_check_collision(self, now_ms, player_rect, timeline):
        if timeline not in self.active_in_timelines:
            return False
        state, t = self.state_at(now_ms)
        if state == 'on' and player_rect.colliderect(self.rect):
            return True
        return False

    def draw(self, surf, camera_x, camera_y, now_ms, timeline):
        if timeline not in self.active_in_timelines:
            return
        state, t = self.state_at(now_ms)
        screen_rect = pygame.Rect(self.rect.x - camera_x, self.rect.y - camera_y, max(2, self.rect.w), max(2, self.rect.h))

        if state == 'off':
            return
        elif state == 'warning':
            pulse = 40 + int(70 * (0.5 + 0.5 * math.sin((t / max(1, self.warning_duration)) * math.pi * 2)))
            surf_l = pygame.Surface((screen_rect.w, screen_rect.h), pygame.SRCALPHA)
            surf_l.fill((255, 0, 0, pulse))
            surf.blit(surf_l, (screen_rect.x, screen_rect.y))
            if self.axis == 'h':
                pygame.draw.line(surf, (120, 0, 0), (screen_rect.x, screen_rect.y + screen_rect.h // 2),
                                 (screen_rect.x + screen_rect.w, screen_rect.y + screen_rect.h // 2), 1)
            else:
                pygame.draw.line(surf, (120, 0, 0), (screen_rect.x + screen_rect.w // 2, screen_rect.y),
                                 (screen_rect.x + screen_rect.w // 2, screen_rect.y + screen_rect.h), 1)
        elif state == 'on':
            surf_l = pygame.Surface((screen_rect.w, screen_rect.h), pygame.SRCALPHA)
            surf_l.fill((255, 0, 0, 220))
            surf.blit(surf_l, (screen_rect.x, screen_rect.y))
            if self.axis == 'h':
                pygame.draw.line(surf, (255, 80, 80), (screen_rect.x, screen_rect.y + screen_rect.h // 2),
                                 (screen_rect.x + screen_rect.w, screen_rect.y + screen_rect.h // 2), 3)
            else:
                pygame.draw.line(surf, (255, 80, 80), (screen_rect.x + screen_rect.w // 2, screen_rect.y),
                                 (screen_rect.x + screen_rect.w // 2, screen_rect.y + screen_rect.h), 3)

# -------------------------
# Player Class
# -------------------------
class Player:
    def __init__(self, x, y, img):
        self.spawn_point = (x, y)
        self.img = img
        self.rect = img.get_rect(topleft=(x, y))
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.dead = False
        self.climbing = False
        self.facing_right = True  # new


    def respawn(self):
        print("Respawn: moving player to spawn")
        self.rect.topleft = self.spawn_point
        self.vel_x = 0
        self.vel_y = 0
        self.dead = False
        self.climbing = False

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        if keys[pygame.K_a]:
            self.vel_x = -4
            self.facing_right = False
        if keys[pygame.K_d]:
            self.vel_x = 4
            self.facing_right = True
        if keys[pygame.K_w] and self.on_ground and not self.climbing:
            self.vel_y = -10
            self.on_ground = False
        if self.climbing:
            if keys[pygame.K_w]:
                self.vel_y = -3
            else:
                self.vel_y = 1.5

    def apply_gravity(self):
        if not self.climbing:
            self.vel_y += 0.5
            if self.vel_y > 10:
                self.vel_y = 10

    def move(self, objects):
        # horizontal collisions
        self.rect.x += self.vel_x
        for obj in objects:
            if isinstance(obj, Block):
                obj = obj.rect
            if self.rect.colliderect(obj):
                if self.vel_x > 0:
                    self.rect.right = obj.left
                elif self.vel_x < 0:
                    self.rect.left = obj.right

        # vertical
        self.rect.y += self.vel_y
        self.on_ground = False
        for obj in objects:
            if isinstance(obj, Block):
                obj = obj.rect
            if self.rect.colliderect(obj):
                if self.vel_y > 0:
                    self.rect.bottom = obj.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = obj.bottom
                    self.vel_y = 0

        # world bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > WORLD_WIDTH:
            self.rect.right = WORLD_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > WORLD_HEIGHT:
            self.rect.bottom = WORLD_HEIGHT
            self.on_ground = True
            self.vel_y = 0

    def check_climb(self, climbables):
        in_climbable = any(self.rect.colliderect(c.rect) for c in climbables)
        if in_climbable and not self.on_ground:
            self.climbing = True
        else:
            self.climbing = False

    def update(self, objects, climbables):
        if not self.dead:
            self.check_climb(climbables)
            self.handle_input()
            self.apply_gravity()
            self.move(objects)

    def draw(self, surf, camera_x, camera_y):
        img = self.img.copy()
        if self.climbing:
            img.fill((0, 255, 0, 100), special_flags=pygame.BLEND_RGBA_MULT)
        if self.dead:
            img.fill((255, 0, 0, 150), special_flags=pygame.BLEND_RGBA_MULT)
        # surf.blit(img, (self.rect.x - camera_x, self.rect.y - camera_y))
        player_img = pygame.image.load("player.png").convert_alpha()
        player_img = pygame.transform.scale(player_img, (32, 48))
        if self.facing_right:
            surf.blit(player_img, (self.rect.x - camera_x, self.rect.y - camera_y))
        else:
            surf.blit(pygame.transform.flip(player_img, True, False), (self.rect.x - camera_x, self.rect.y - camera_y)) 


# -------------------------
# Load player image
# -------------------------
try:
    player_img = pygame.image.load("player.png").convert_alpha()
    player_img = pygame.transform.scale(player_img, (32, 48))
except Exception as e:
    print("Warning: couldn't load player.png:", e)
    player_img = pygame.Surface((32, 48), pygame.SRCALPHA)
    player_img.fill((200, 200, 0))

player = Player(900, 1100, player_img)

class Block:
    def __init__(self, x, y, w, h, image=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.image = None
        if image:
            self.image = pygame.transform.scale(image, (w, h))

    def draw(self, surf, camera_x, camera_y):
        if self.image:
            surf.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))
        else:
            pygame.draw.rect(surf, (150, 150, 150),  # fallback gray
                             pygame.Rect(self.rect.x - camera_x,
                                         self.rect.y - camera_y,
                                         self.rect.w, self.rect.h))

class Climbable:
    def __init__(self, x, y, w, h, image=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.image = None
        if image:
            self.image = pygame.transform.scale(image, (w, h))

    def draw(self, surf, camera_x, camera_y):
        if self.image:
            surf.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))
        else:
            pygame.draw.rect(surf, (0, 255, 0),  # fallback gray
                             pygame.Rect(self.rect.x - camera_x,
                                         self.rect.y - camera_y,
                                         self.rect.w, self.rect.h))

# -------------------------
# World Objects
# -------------------------

tree_img = pygame.image.load("bigTree.png").convert_alpha()
specialBlock = Block(1350, 400, 300, 750, tree_img) # BigTree
def build_world():
    # Past
    cliff_img = pygame.image.load("cliff.png").convert_alpha()
    cliff_img = pygame.transform.scale(cliff_img, (800, 500))
    cliff2_img = pygame.image.load("cliffM.png").convert_alpha()
    cliff2_img = pygame.transform.scale(cliff2_img, (800, 500))
    ground_img = pygame.image.load("ground2.png").convert_alpha()
    ground_img = pygame.transform.scale(ground_img, (800, 500))
    rock_img = pygame.image.load("rocks.png").convert_alpha()
    rock_img = pygame.transform.scale(rock_img, (1000, 500))
    bPlatform_img = pygame.image.load("bluePlatform.png").convert_alpha()
    bPlatform_img = pygame.transform.scale(bPlatform_img, (1000, 500))
    gPlatform_img = pygame.image.load("actualBluePlatform.png").convert_alpha()
    gPlatform_img = pygame.transform.scale(gPlatform_img, (1000, 500))
    vault_img = pygame.image.load("vaultDoor.png").convert_alpha()
    vault_img = pygame.transform.scale(vault_img, (300, 500))


    past = [
        Block(0, 1150, WORLD_WIDTH, 50, ground_img),  # ground at bottom
        Block(0, 400, 800, 500, cliff_img),         # tall cliff on left
        Block(2000, 400, 400, 800, cliff2_img),        # tall cliff on right
        Block(200, 825, 400, 350, rock_img),       # cave blockage
        
        # Block(1900, 1080, 200, 70),
        # Block(1600, 600, 200, 40),
    ]

    # Present
    
    present = [
        Block(0, 1150, WORLD_WIDTH, 50, ground_img),  # ground
        Block(0, 400, 800, 500, cliff_img),         # tall cliff
        Block(650, 893, 100, 260, vault_img),        # vault door
        Block(2000, 400, 400, 800, cliff2_img),        # tall cliff on right


        Block(1225, 650, 200, 40, bPlatform_img), # floating platform
        Block(1600, 600, 200, 40, gPlatform_img), # floating platform
        specialBlock, # BigTree
    ]

    return past, present

past_objects, present_objects = build_world()

# -------------------------
# Climbable vines
# -------------------------
vines_img = pygame.image.load("vines.png").convert_alpha()
vines_img = pygame.transform.scale(vines_img, (800, 500))
climbables_past = [Climbable(770, 400, 50, 500, vines_img)]
climbables_present = [Climbable(1975, 400, 50, 750, vines_img)]


# -------------------------
# Seed class (tracks created tree parts)
# -------------------------
class Seed:
    def __init__(self, x, y):
        self.original_pos = (x, y)
        self.rect = pygame.Rect(x, y, 32, 32)
        self.picked_up = False
        self.placed = False
        self.grown_in_present = False
        self.placedInPresent = False
        # tree parts references (for removal)
        self.tree_trunk = None
        self.tree_top = None

    def reset(self):
        print("Seed.reset(): removing any grown tree & resetting seed to original position")
        # remove grown tree parts if present
        if self.tree_trunk is not None:
            if self.tree_trunk in climbables_present:
                climbables_present.remove(self.tree_trunk)
                print(" - removed trunk from climbables_present")
            self.tree_trunk = None
        self.rect.topleft = self.original_pos
        self.picked_up = False
        self.placed = False
        self.grown_in_present = False
        self.placedInPresent = False

    def draw(self, surf, camera_x, camera_y, timeline):
        # unpicked + unplaced seed visible only in past
        if timeline == "past" and not self.picked_up and not self.placed:
            # pygame.draw.rect(surf, (255, 255, 0),
            #                  pygame.Rect(self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height))
            seed_img = pygame.image.load("seed.png").convert_alpha()
            seed_img = pygame.transform.scale(seed_img, (32, 32))
            surf.blit(seed_img, (self.rect.x - camera_x, self.rect.y - camera_y))
        # show placed seed marker in either timeline
        if (self.placed) and ((timeline == 'past' and self.grown_in_present) or (timeline == 'present' and self.placedInPresent)):
            mound_img = pygame.image.load("mound.png").convert_alpha()
            mound_img = pygame.transform.scale(mound_img, (32, 32))
            surf.blit(mound_img, (self.rect.x - camera_x, self.rect.y - camera_y + 10))
            # pygame.draw.rect(surf, (180, 120, 60),
            #                  pygame.Rect(self.rect.x - camera_x, self.rect.y - camera_y, self.rect.width, self.rect.height))

# create one seed
seed = Seed(110, 1100)
seeds_past = [seed]
inventory = []

# -------------------------
# Lasers
# -------------------------
# We'll create one horizontal laser in the present that spans across x=1000..1400 at y=900 (thin).
# It will be absent in the past (only present).
laser_rect_present1 = pygame.Rect(250, 900, 25, 250)  # thin horizontal rect
laser1 = Laser(laser_rect_present1, axis='v', off_duration=2000, warning_duration=1000, on_duration=3000, active_in_timelines=('present',), start_offset=3000)

laser_rect_present2 = pygame.Rect(350, 900, 25, 250)  # thin horizontal rect
laser2 = Laser(laser_rect_present2, axis='v', off_duration=2000, warning_duration=1000, on_duration=3000, active_in_timelines=('present',), start_offset=2000)

laser_rect_present3 = pygame.Rect(450, 900, 25, 250)  # thin horizontal rect
laser3 = Laser(laser_rect_present3, axis='v', off_duration=2000, warning_duration=1000, on_duration=3000, active_in_timelines=('present',), start_offset=1000)

laser_rect_present4 = pygame.Rect(550, 900, 25, 250)  # thin horizontal rect
laser4 = Laser(laser_rect_present4, axis='v', off_duration=2000, warning_duration=1000, on_duration=3000, active_in_timelines=('present',), start_offset=0)


# Add more laser instances if needed:
# laser2 = Laser(pygame.Rect(...), axis='v', ...)
lasers_present = [laser1, laser2, laser3, laser4]
lasers_past = []

# -------------------------
# Tree class
# -------------------------
class Tree:
    def __init__(self, x, y, height=120, width=50, trunk_img="treeTrunk.png", top_img="treeTop.png"):
        trunk_img = pygame.image.load(trunk_img).convert_alpha()
        trunk_img = pygame.transform.scale(trunk_img, (800, 500))
        self.trunk = Climbable(x, y - height, width, height, trunk_img) #pygame.Rect(x, y - height, width, height)
        self.top = None

        if top_img:
            top_img = pygame.image.load(top_img).convert_alpha()
            topWidth = 5/3 * width * 2; topHeight = height/2
            top_img = pygame.transform.scale(top_img, (800, 500))
            self.top = Block(x - topWidth/3, y - height - topHeight/2, topWidth, topHeight, top_img) #pygame.Rect(x - 10, y - height - 10, 5/3 * width, 10)

        self.support = Block(x + width/2 - 2.5, y - height, 5, height) #pygame.Rect(x + width/2 - 2.5, y - height, 5, height)  # small platform on top of trunk
        self.alive = True

    def add_to_world(self):
        if self.alive:
            climbables_past.append(self.trunk)
            if self.top:
                past_objects.append(self.top)
            past_objects.append(self.support)

    def remove_from_world(self):
        if self.trunk in climbables_past:
            climbables_past.remove(self.trunk)
        if self.top and self.top in past_objects:
            past_objects.remove(self.top)
        if self.support in past_objects:
            past_objects.remove(self.support)
    
    def kill(self):
        self.alive = False

    def draw(self, surf, camera_x, camera_y, timeline):
        if not self.alive:
            self.remove_from_world()
            return
        # Trees only drawn in present OR past (if you want some to exist there)
        self.trunk.draw(surf, camera_x, camera_y)
        if self.top:
            self.top.draw(surf, camera_x, camera_y)


# -------------------------
# Axe class
# -------------------------
class Axe:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 50)
        self.picked_up = False

    def reset(self):
        self.picked_up = False

    def draw(self, surf, camera_x, camera_y, timeline):
        if not self.picked_up and timeline == "present":
            axe_img = pygame.image.load("axe.png").convert_alpha()
            axe_img = pygame.transform.scale(axe_img, (40, 50))
            surf.blit(axe_img, (self.rect.x - camera_x, self.rect.y - camera_y))
       

# -------------------------
# Setup example axe + pre-existing tree
# -------------------------
axe = Axe(250, 350)
inventory = []
trees = []

# Example: add one pre-existing tree at x=1000, ground y=550
tree1 = Tree(1100, 1150)
tree2 = Tree(1400, 1150, trunk_img="bigTree.png", top_img=None, height=200, width=80)
specialTree = tree2
tree1.add_to_world()
tree2.add_to_world()
trees.append(tree1)
trees.append(tree2)

## Star Class
star_img = pygame.image.load("star.png").convert_alpha()
star_img = pygame.transform.scale(star_img, (40, 40))  # adjust size

class Star:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.collected = False

    def draw(self, surf, camera_x, camera_y):
        if not self.collected:
            surf.blit(star_img, (self.rect.x - camera_x, self.rect.y - camera_y))

star = Star(1305, 600)  # position somewhere hard to reach



# -------------------------
# Colors
# -------------------------
PAST_COLOR = (100, 200, 100)
PRESENT_COLOR = (100, 100, 200)

# -------------------------
# Camera
# -------------------------
def get_camera(player_rect):
    camera_x = player_rect.centerx - WIDTH // 2
    camera_y = player_rect.centery - HEIGHT // 2
    camera_x = max(0, min(camera_x, WORLD_WIDTH - WIDTH))
    camera_y = max(0, min(camera_y, WORLD_HEIGHT - HEIGHT))
    return camera_x, camera_y


# HUD slot background
slot_img = pygame.image.load("slot.png").convert_alpha()
slot_img = pygame.transform.scale(slot_img, (50, 50))

# Item icons
seed_icon   = pygame.image.load("seed.png").convert_alpha()
seed_icon = pygame.transform.scale(seed_icon, (40, 40))
axe_icon    = pygame.image.load("axe.png").convert_alpha()
axe_icon = pygame.transform.scale(axe_icon, (40, 40))
bucket_icon = pygame.image.load("bucket.png").convert_alpha()
bucket_icon = pygame.transform.scale(bucket_icon, (40, 40))

def draw_hud(surf, inventory):
    # HUD position
    start_x = 20
    start_y = 20
    spacing = 60  # space between slots

    items = ["seed", "axe", "bucket"]
    icons = {
        "seed": seed_icon,
        "axe": axe_icon,
        "bucket": bucket_icon
    }

    for i, item in enumerate(items):
        x = start_x + i * spacing
        y = start_y

        # Draw slot background
        surf.blit(slot_img, (x, y))

        # If the item is in inventory, draw it
        if item in inventory:
            surf.blit(icons[item], (x + 5, y + 5))  # small padding


# -------------------------
# Game loop
# -------------------------
current_time = "present"
running = True
victory = False
teleport_sound = pygame.mixer.Sound("TeleportSound.mp3")
teleport_sound.set_volume(0.1)
darken_overlay = pygame.Surface((WIDTH, HEIGHT))
darken_overlay.set_alpha(100)      # 0 = fully transparent, 255 = fully black
darken_overlay.fill((0, 0, 0))

while running:
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False


        # KEYDOWN handling (Q/E should be handled here so they trigger once per press)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s and not player.dead:
                # swap timeline first, then check if swap killed player
                current_time = "past" if current_time == "present" else "present"
                teleport_sound.play()
                new_objects = past_objects if current_time == "past" else present_objects
                if any(player.rect.colliderect(obj.rect) for obj in new_objects):
                    player.dead = True
                    print("Player died because they swapped into a block")
            elif event.key == pygame.K_r and player.dead:
                print("Player requested respawn")
                player.respawn()
                current_time = "present"
                # reset seeds and remove any trees
                for s in seeds_past:
                    s.reset()
                inventory.clear()
                print(" - inventory cleared, seeds reset")
            elif event.key == pygame.K_q:
                if not axe.picked_up and player.rect.colliderect(axe.rect) and current_time == "present":
                    axe.picked_up = True
                    print("Picked up Axe!")

                # pick up seed only in past
                if current_time != "past":
                    print("Q pressed but not in past - cannot pick seed here")
                else:
                    picked_any = False
                    for s in seeds_past:
                        if not s.picked_up and not s.placed and player.rect.colliderect(s.rect):
                            s.picked_up = True
                            inventory.append(s)
                            picked_any = True
                            print(f"Picked up seed at {s.rect.topleft}")
                            break
                    if not picked_any:
                        print("Q pressed but no pickable seed under player")
            elif event.key == pygame.K_e:
                # place the first seed in inventory
                if axe.picked_up and current_time == "past":
                    for t in trees:
                        if t.alive and player.rect.colliderect(t.trunk.rect.inflate(50, 0)):
                            print("Tree chopped down!")
                            if t == specialTree:
                                present_objects.remove(specialBlock)
                            t.remove_from_world()
                            t.kill()
                
                if not inventory:
                    print("E pressed but inventory empty")
                elif player.on_ground:
                    s = inventory.pop(0)
                    # place at player's feet
                    s.rect.bottom = player.rect.bottom + 1
                    s.rect.x = player.rect.centerx - s.rect.width // 2
                    s.placed = True
                    s.picked_up = False
                    print(f"Placed seed in '{current_time}' at {s.rect.topleft}")
                    # If placed in past and touching ground, mark for growth
                    if current_time == "past":
                        touching_ground = any(s.rect.colliderect(obj.rect) for obj in past_objects)
                        if touching_ground:
                            s.grown_in_present = True
                            print(" -> Seed is on ground in the past and will grow in the present.")
                        else:
                            print(" -> Seed not touching ground; it will NOT grow.")
                    else:
                        s.placedInPresent = True
                        print(" -> Seed placed in present; this does nothing (by design).")

    # active lists based on timeline
    objects = past_objects if current_time == "past" else present_objects
    climbables = climbables_past if current_time == "past" else climbables_present
    lasers = lasers_past if current_time == "past" else lasers_present

    # If a seed is flagged grown_in_present and we are in the present and its tree isn't created, create it now
    for s in seeds_past:
        if s.grown_in_present and current_time == "present" and s.tree_trunk is None:
            # create trunk (climbable only) and small top platform (solid)
            trunk_w, trunk_h = 40, 250
            trunk_x = s.rect.x + s.rect.width // 2 - trunk_w // 2
            trunk_y = s.rect.y - trunk_h + 32  # 16 to offset seed height
            beanstalk_img = pygame.image.load("beanstalk.png").convert_alpha()
            beanstalk_img = pygame.transform.scale(beanstalk_img, (trunk_w, trunk_h))
            trunk = Climbable(trunk_x, trunk_y, trunk_w, trunk_h, beanstalk_img)
            s.tree_trunk = trunk

            climbables_present.append(trunk)     # climbable area only
            print(f"Tree grown for seed at {s.rect.topleft} => trunk {trunk.rect.topleft}, top top_platform.topleft") # changed debug

    # Update lasers -> check lethal collisions
    for laser in lasers:
        if laser.update_and_check_collision(now, player.rect, current_time):
            player.dead = True
            print("Player died from laser while it was ON")
    
    # Update star collection
    if not star.collected and player.rect.colliderect(star.rect):
        star.collected = True
        victory = True


    # Update player
    player.update(objects, climbables)
    camera_x, camera_y = get_camera(player.rect)

    if current_time == "present":
        screen.blit(background_present, (0, 0))
    else:
        screen.blit(background_past, (0, 0))

    screen.blit(darken_overlay, (0, 0))

    # Draw world
    color = PAST_COLOR if current_time == "past" else PRESENT_COLOR
    for obj in objects:
        obj.draw(screen, camera_x, camera_y)
    
    # draw star
    star.draw(screen, camera_x, camera_y)

    # draw climbables
    for c in climbables:
        c.draw(screen, camera_x, camera_y)

    # draw seeds
    for s in seeds_past:
        s.draw(screen, camera_x, camera_y, current_time)

    # draw lasers
    for laser in lasers:
        laser.draw(screen, camera_x, camera_y, now, current_time)

    # draw player
    player.draw(screen, camera_x, camera_y)

    # draw axe
    axe.draw(screen, camera_x, camera_y, current_time)

    # draw trees
    if current_time == "past":
        for t in trees:
            if t.alive:
                t.add_to_world()
                t.draw(screen, camera_x, camera_y, current_time)
            else:
                t.remove_from_world()
    else:
        for t in trees:
            t.remove_from_world()

    # draw HUD
    draw_hud(screen, [] + (["seed"] if any(s.picked_up for s in seeds_past) else []) + (["axe"] if axe.picked_up else []))

    # HUD / debug
    if player.dead:
        font = pygame.font.SysFont(None, 36)
        text = font.render("You Died! Press R to Respawn", True, (255, 0, 0))
        screen.blit(text, (200, 200))

    # small debug prints on-screen for inventory/seed state
    dbg_font = pygame.font.SysFont(None, 20)
    screen.blit(dbg_font.render(f"Current coordinates: : {player.rect.x}, {player.rect.y}", True, (220,220,220)), (10, 70))
    screen.blit(dbg_font.render(f"Current timeline: {current_time}", True, (220,220,220)), (10, 90))

    if victory:
    # Fill background
        screen.fill((0, 0, 0))

        # Large gold text
        font = pygame.font.Font(None, 72)  # use default font (safer than SysFont)
        text = font.render("VICTORY!", True, (255, 215, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        screen.blit(text, text_rect)

        # Subtext in white
        sub_font = pygame.font.Font(None, 36)
        sub_text = sub_font.render("Press ESC to quit", True, (255, 255, 255))
        sub_rect = sub_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
        screen.blit(sub_text, sub_rect)

    pygame.display.flip()  # make sure it shows
    clock.tick(60)

pygame.quit()
sys.exit()
