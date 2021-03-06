"""
Глобальные нужные вещи (камера, константы, переменные)
"""
import pygame
import ctypes


def from_local_to_global_pos(x, y):
    return x - CAMERA.all_x_offset, y - CAMERA.all_y_offset


def from_global_to_local_pos(global_x, global_y):
    return global_x + CAMERA.all_x_offset, global_y + CAMERA.all_y_offset


def change_draw_area(new_left, new_top, new_right, new_bottom):
    draw_area["l"] = new_left
    draw_area["t"] = new_top
    draw_area["r"] = new_right
    draw_area["b"] = new_bottom


def update_statistics(name_of_mob, cur):
    res = cur.execute("SELECT kills FROM Info WHERE name = '{}'".format(name_of_mob)).fetchone()[0]
    cur.execute("""UPDATE Info
                            SET kills = {}
                            WHERE name = '{}'""".format(res + temp_stats[name_of_mob], name_of_mob))
    temp_stats[name_of_mob] = 0


class LayeredUpdates(pygame.sprite.LayeredUpdates):
    def draw(self, surface: pygame.Surface):
        for sprite in self.sprites():
            if not (sprite.rect.right < draw_area["l"] - 100 or sprite.rect.left > draw_area["r"] + 100 or
                    sprite.rect.bottom < draw_area["t"] - 100 or sprite.rect.top > draw_area["b"] + 100):
                try:
                    if type(sprite) == Hitbox:
                        rect = pygame.Rect(*from_global_to_local_pos(sprite.rect.x, sprite.rect.y), sprite.rect.w,
                                           sprite.rect.h)
                    else:
                        rect = sprite.rect
                    surface.blit(sprite.image, rect)
                except pygame.error:
                    pass


class Hitbox(pygame.sprite.Sprite):
    def __init__(self, dx, dy, width, height, parent, can_slide):
        super().__init__(hitbox_group)  # add second argument "all_sprites" to show image of hitbox
        self.rect = pygame.Rect(0, 0, width, height)
        self.image = pygame.Surface((width, height))
        self.dx, self.dy = dx, dy
        self.parent: BaseGameObject = parent
        self.can_slide = can_slide

    def set_pos(self, x, y):
        self.rect.x, self.rect.y = int(x + self.dx), int(y + self.dy)

    def get_colliding_objects(self, include_team_members=False, include_not_slidable_obj=False):
        temp = pygame.sprite.spritecollide(self, hitbox_group, False)
        temp.remove(self)

        if not include_not_slidable_obj:
            temp = list(filter(lambda x: x.can_slide, temp))

        if include_team_members:
            return temp
        return list(filter(lambda x: x.parent.team != self.parent.team or x.parent.team is None, temp))


class Camera:
    def __init__(self):
        self.min_speed = 1
        self.all_x_offset = self.all_y_offset = 0

    def update(self, target):
        if target.alive():
            self.all_x_offset -= target.rect.x + target.rect.w / 2 - WIDTH / 2
            self.all_y_offset -= target.rect.y + target.rect.h / 2 - HEIGHT / 2


class BaseGameObject(pygame.sprite.Sprite):
    def __init__(self, x, y, img, hitbox=None, team=None, can_slide=True):  # hitbox = [dx, dy, width, height]
        self.str_image = img
        self.__animation_path = None
        self.initial_image = self.image = pygame.image.load(f"files/img/{img}").convert_alpha()
        self.avg_color = pygame.transform.average_color(self.image)
        self.rect = self.image.get_rect()
        self.global_x, self.global_y = x, y
        self.team = team
        self.__animations = {}  # structure {"name-of-animation": ['loaded_image'... ]}
        self.__current_animation = None
        self.__animation_counter = 0
        self.__current_animation_once = False
        self.__animation_queue = []

        if hitbox:
            if hitbox == HITBOX_ARROW:
                self.hitbox = Hitbox(0, 16, self.rect.w, self.rect.h, self, can_slide)
            elif hitbox == HITBOX_FULL_RECT:
                self.hitbox = Hitbox(0, 0, self.rect.w, self.rect.h, self, can_slide)
            else:
                self.hitbox = Hitbox(*hitbox, self, can_slide)
            self.hitbox.set_pos(self.global_x, self.global_y)
        else:
            self.hitbox = None

        super().__init__(all_sprites)
        all_sprites.change_layer(self, self.global_y + self.rect.h)

    def add_animation(self, name, path):
        """
        Adds the animation
        name - name of animation [string]
        path - path to folder with frames of animation [string]
        Example:
             name - up
             path - Spearman/up
        """
        self.__animations[name] = []
        self.__animation_path = path.split('/')[0]
        counter = 1
        while True:
            try:
                frame = pygame.image.load(f'files/img/{path}/{counter}.png').convert_alpha()
                self.__animations[name].append(frame)
                counter += 1
            except FileNotFoundError:
                break

    def play_animation(self, name: str, once=False, play_now=True):
        """ Plays an animation with the name 'name'
            This can be called even if the current animation is an animation with the name 'name'
        """
        if self.__current_animation != name:
            if play_now or self.__current_animation is None:
                self.__animation_counter = 0
                self.__current_animation = name
                self.__animation_queue.clear()
                self.__animation_queue.append(name)
            else:
                self.__animation_queue.append(name)
            self.__current_animation_once = once
            if not (self in play_animation_group):
                play_animation_group.append(self)

    def stop_animation(self):
        """Stops the current animation"""
        if self.__current_animation:
            self.str_image = f'{self.__animation_path}/{self.__current_animation}/{1}.png'
            self.image = self.__animations[self.__current_animation][0]
            self.__animation_queue.pop(0)
            if len(self.__animation_queue) == 0:
                self.__current_animation = None
                play_animation_group.remove(self)
            else:
                self.__current_animation = self.__animation_queue[0]
                self.image = self.__animations[self.__current_animation][0]

    def change_image(self):
        try:
            self.image = self.__animations[self.__current_animation][self.__animation_counter]
            self.__animation_counter += 1
            if self.__animation_counter >= len(self.__animations[self.__current_animation]):
                self.__animation_counter = 0
                if self.__current_animation_once or len(self.__animation_queue) >= 2:
                    self.stop_animation()
            if self.__current_animation:
                self.str_image = f'{self.__animation_path}/{self.__current_animation}/{self.__animation_counter + 1}.png'
        except IndexError or KeyError as e:
            print(e)

    def get_current_animation(self):
        return self.__current_animation

    def set_pos(self, glob_x, glob_y):
        self.global_x, self.global_y = glob_x, glob_y

    def update(self):
        self.rect.x, self.rect.y = [i for i in from_global_to_local_pos(self.global_x, self.global_y)]

    def die(self):
        delete_later.append(self)


ctypes.windll.user32.SetProcessDPIAware()
true_res = (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))

multiplayer_game = False
multiplayer_obj_id = 0
HITBOX_ARROW = 1
HITBOX_FULL_RECT = 2
PLAYER_TEAM = "player"
ENEMY_TEAM = "enemy"
FPS = 100
WIDTH = true_res[0]
HEIGHT = true_res[1]
TILE_SIZE = TILE_WIDTH, TILE_HEIGHT = (64, 64)

all_sprites = LayeredUpdates()
particle_group = LayeredUpdates()
hitbox_group = pygame.sprite.Group()
items_text = pygame.sprite.Group()
delete_later = []
play_animation_group = []
draw_area = {"l": 0, "t": 0, "r": WIDTH, "b": HEIGHT}  # left top right bottom
take_damage = []  # for multiplayer

CAMERA = Camera()

# Statistics stuff below
temp_stats = {
    "MiniGolem": 0,
    "Snake": 0,
    "Dog": 0,
    "Tree": 0,
    "IceSoul": 0,
    "FireSoul": 0,
    "DragonBoss": 0,
    "NecroBoss": 0,
    "Hunter": 0,
    "Golem": 0
}