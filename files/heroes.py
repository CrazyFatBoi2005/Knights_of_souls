import random
import pygame.mouse
import math
from threading import Timer
from files import units_characteristics
from files.global_stuff import *
from files.particles import SquareParticle


class BaseHero(BaseGameObject):
    def __init__(self, x, y, image, hp, armor, protection, walk_speed, run_speed, attack_cooldown, damage, anim_folder):
        self.dead = False
        self.max_hp = self.hp = hp
        self.max_armor = self.armor = armor
        self.protection = protection
        self.initial_walk_speed = self.walk_speed = walk_speed
        self.initial_run_speed = self.run_speed = run_speed
        self.attack_cooldown = attack_cooldown
        self.damage = damage
        self.running = False
        self.gun = None
        self.velocity = pygame.Vector2(0, 0)
        super().__init__(x, y, image, [11, 36, 27, 22], PLAYER_TEAM)
        self.damage_multiplier = 1
        self.candle_damage = 0  # для предмета "свеча"
        self.has_cross = False  # for item Cross
        self.has_welding_helmet = False
        self.has_mirror = False
        self.has_electric_ring = False
        self.apple_bag_count = 0
        self.vampirism = 0  # FLOAT
        self.slowing_down_effect_timer = None
        self.armor_heal_timer = None

        # настройка анимаций
        self.add_animation('up', anim_folder + '/up')
        self.add_animation('left', anim_folder + '/left')
        self.add_animation('right', anim_folder + '/right')
        self.add_animation('down', anim_folder + '/down')

    def key_input(self, keystates=None):
        if not keystates and not multiplayer_game:
            keystates = pygame.key.get_pressed()
        self.velocity.x = self.velocity.y = 0
        if keystates[pygame.K_a]:
            self.velocity.x += -1
        if keystates[pygame.K_d]:
            self.velocity.x += 1
        if keystates[pygame.K_w]:
            self.velocity.y += -1
        if keystates[pygame.K_s]:
            self.velocity.y += 1
        if not self.velocity.is_normalized() and self.velocity.length() != 0:
            self.velocity.normalize_ip()

        if self.velocity.length() == 0:
            self.stop_animation()
            return

        if self.velocity.y > 0 and self.velocity.x == 0:
            self.play_animation("down")
        elif self.velocity.y < 0 and self.velocity.x == 0:
            self.play_animation("up")

        if self.velocity.x > 0:
            self.play_animation("right")
        elif self.velocity.x < 0:
            self.play_animation("left")

    def attack(self, x, y):  # Чтобы ошибка не возникала
        pass

    def update(self):

        if self.running:
            move_x, move_y = self.velocity.x * self.run_speed, self.velocity.y * self.run_speed
        else:
            move_x, move_y = self.velocity.x * self.walk_speed, self.velocity.y * self.walk_speed

        self.global_x += move_x
        self.hitbox.set_pos(self.global_x, self.global_y)
        if self.hitbox.get_colliding_objects(include_not_slidable_obj=False):
            self.global_x -= move_x
            self.hitbox.set_pos(self.global_x, self.global_y)

        self.global_y += move_y
        self.hitbox.set_pos(self.global_x, self.global_y)
        if self.hitbox.get_colliding_objects(include_not_slidable_obj=False):
            self.global_y -= move_y
            self.hitbox.set_pos(self.global_x, self.global_y)

        all_sprites.change_layer(self, self.global_y + self.rect.h)
        super().update()

    def take_damage(self, damage, from_candle=False, count_of_particles=10, from_poison=False, from_vampirism=False):
        """from_candle НЕНАДО ставить TRUE. Это только для предмета свеча"""
        if self.armor_heal_timer:
            self.armor_heal_timer.cancel()
        if not from_poison and not from_vampirism:
            damage = (damage - self.protection) * self.damage_multiplier
        else:
            damage = damage * self.damage_multiplier
        if damage > 0:
            if from_poison or from_vampirism:
                self.hp -= damage
            else:
                self.armor -= damage
            if self.armor < 0:
                self.hp -= abs(self.armor)
                self.armor = 0

            if self.hp <= 0:
                if self.has_cross:  # если есть крест не убиваем
                    self.hp = self.max_hp
                    self.armor = self.max_armor
                    self.damage_multiplier = 0  # дается бессмертие на 3 секунды
                    self.has_cross = False
                    Timer(3, self.change_damage_multiplier, [1]).start()  # убираем бессмертие
                else:
                    self.die()

        if self.candle_damage and not from_candle and damage:
            Timer(1, self.take_damage, [self.candle_damage, True]).start()
            Timer(2, self.take_damage, [self.candle_damage, True]).start()

        if self.alive():
            if from_candle:
                SquareParticle.create_particles(self.global_x + self.rect.w // 2, self.global_y + self.rect.h // 2,
                                                pygame.Color("orange"), count_of_particles)
            elif from_poison:
                SquareParticle.create_particles(self.global_x + self.rect.w // 2, self.global_y + self.rect.h // 2,
                                                pygame.Color((73, 187, 34)), count_of_particles)
            elif self.armor <= 0 or from_vampirism:
                SquareParticle.create_particles(self.global_x + self.rect.w // 2, self.global_y + self.rect.h // 2,
                                                pygame.Color("red"), count_of_particles)
            else:
                SquareParticle.create_particles(self.global_x + self.rect.w // 2, self.global_y + self.rect.h // 2,
                                                pygame.Color("Light grey"), count_of_particles)
            self.armor_heal_timer = Timer(4, self.heal_armor)
            self.armor_heal_timer.start()

    def heal(self, value):
        self.hp += value
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def increase_damage(self, value):  # увеличить урон
        self.damage += value
        if self.gun:
            self.gun.damage += value

    def change_damage_multiplier(self, val):
        self.damage_multiplier = val

    def get_slowing_down_effect(self, time, value):  # 0.00 < value <= 1
        self.run_speed = self.initial_run_speed * value
        self.walk_speed = self.initial_walk_speed * value
        if self.slowing_down_effect_timer:
            self.slowing_down_effect_timer.cancel()
        self.slowing_down_effect_timer = Timer(time, self.remove_slowing_down_effect)
        self.slowing_down_effect_timer.start()

    def remove_slowing_down_effect(self):
        self.run_speed = self.initial_run_speed
        self.walk_speed = self.initial_walk_speed

    def heal_armor(self):
        self.armor += 1
        if self.armor < self.max_armor:
            self.armor_heal_timer = Timer(0.2, self.heal_armor)
            self.armor_heal_timer.start()
        else:
            self.armor = self.max_armor


class SpearMan(BaseHero):
    characteristic = "Throws spears like a master", "10% chance to deal triple damage"

    def __init__(self, x=0, y=0):
        data = units_characteristics.spearman
        super().__init__(x, y, data["img"], data["hp"], data["armor"], data["protection"], data["walk_speed"],
                         data["run_speed"], data["attack_cooldown"], data["damage"], 'SpearMan')
        self.gun = Spear(x, y, self.team, data["damage"], self)

        self.new_spear_timer = None
        self.spear_dx, self.spear_dy = 30, 5

    def attack(self, x, y):
        self.running = False
        if self.gun:
            self.gun.shot()
            self.gun = None
            self.new_spear_timer = Timer(self.attack_cooldown, self.new_spear)
            self.new_spear_timer.daemon = True
            self.new_spear_timer.start()

    def new_spear(self):
        if self.alive():
            self.gun = Spear(self.global_x, self.global_y, self.team, self.damage, self)
            self.look_at_mouse()

    def look_at_mouse(self):
        if not self.gun.shooted:
            x, y = from_local_to_global_pos(*pygame.mouse.get_pos())
            self.gun.angle = pygame.Vector2(x - self.global_x - self.gun.rect.w // 2, y - self.global_y
                                            - self.gun.rect.h // 2).normalize().angle_to(pygame.Vector2(1, 0))
            if self.gun.angle < 0:
                self.gun.angle += 360
            self.gun.image = pygame.transform.rotate(self.gun.orig_image, self.gun.angle)
            self.gun.set_pos(self.global_x + 40 * math.cos(self.gun.angle / 180 * math.pi) + 3,
                             self.global_y - 40 * math.sin(self.gun.angle / 180 * math.pi) + 15)

    def die(self):
        if self.new_spear_timer:
            self.new_spear_timer.cancel()
        if self.gun:
            self.gun.die()
        super().die()


class Spear(BaseGameObject):
    def __init__(self, x, y, team, damage, parent: SpearMan):
        self.damage = damage
        self.parent = parent
        self.angle = 0
        self.speed = 10
        self.shooted = False
        self.vector = pygame.Vector2(0, 0)

        super().__init__(x, y, units_characteristics.spearman['gun_img'], HITBOX_ARROW, team, False)
        self.orig_image = self.image

    def shot(self):
        self.vector = pygame.Vector2(1, 0).rotate(-self.angle).normalize()
        self.hitbox.mask = pygame.mask.from_surface(self.image)
        self.shooted = True

    def update(self):
        all_sprites.change_layer(self, self.hitbox.rect.bottom)
        if self.shooted:
            self.global_x += self.vector.x * self.speed
            self.global_y += self.vector.y * self.speed
            for i in self.hitbox.get_colliding_objects():
                if pygame.sprite.collide_mask(self.hitbox, i):
                    if hasattr(i.parent, "hp"):
                        dmg = self.damage * 3 if random.randrange(1, 11) == 9 else self.damage
                        self.parent.heal(dmg * self.parent.vampirism)
                        if dmg == self.damage * 3:
                            i.parent.take_damage(dmg, count_of_particles=30)
                        else:
                            i.parent.take_damage(dmg)

                        if self.parent.candle_damage:
                            for g in [1, 2, 3, 4, 5]:
                                t = Timer(g, i.parent.take_damage, [self.parent.candle_damage, True])
                                t.daemon = True
                                t.start()
                    else:
                        SquareParticle.create_particles(self.global_x, self.global_y,
                                                        i.parent.avg_color)
                    self.die()
        self.hitbox.set_pos(self.global_x, self.global_y)
        super().update()


class MagicMan(BaseHero):
    characteristic = "Creates an ice toxin from the ground", "enemies slow down when hit"

    def __init__(self, x=0, y=0):
        data = units_characteristics.magicman
        self.can_shot = True
        self.attack_range = data["attack_range"]
        super().__init__(x, y, data["img"], data["hp"], data["armor"], data["protection"], data["walk_speed"],
                         data["run_speed"], data["attack_cooldown"], data["damage"], 'MagicMan')
        super().update()

    def attack(self, x, y):
        self.running = False
        if self.can_shot:
            x, y = from_local_to_global_pos(x, y)
            vector = pygame.Vector2(x - self.global_x, y - self.global_y)
            if vector.length() >= self.attack_range:
                vector = vector.normalize() * self.attack_range + (self.global_x, self.global_y)
                x, y = vector.x, vector.y
            fire = MagicManFire(x, y, self.damage, self.team, self)
            self.can_shot = False
            Timer(self.attack_cooldown, self.enable_shot).start()
            Timer(1, fire.die).start()

    def enable_shot(self):
        self.can_shot = True


class MagicManFire(BaseGameObject):
    def __init__(self, x, y, damage, team, parent):
        self.damage = damage
        self.parent = parent
        self.damage_taken = []
        super().__init__(x - 50, y - 20, units_characteristics.magicman["gun_img"], HITBOX_FULL_RECT, team, False)
        all_sprites.change_layer(self, 0)

    def update(self):
        for i in self.hitbox.get_colliding_objects():
            if i in self.damage_taken:
                continue
            if hasattr(i.parent, "hp"):
                i.parent.take_damage(self.damage)
                i.parent.get_slowing_down_effect(time=2, value=0.5)
                if self.parent.candle_damage:
                    Timer(1, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                    Timer(2, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                    Timer(3, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                    Timer(4, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                    Timer(5, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                self.parent.heal(self.damage * self.parent.vampirism)
            self.damage_taken.append(i)
        super().update()


class SwordMan(BaseHero):
    characteristic = "Deals penetrating blows with a rapier", "Takes 1 less damage from any source", "thanks to his armor"

    def __init__(self, x=0, y=0):
        data = units_characteristics.swordman
        self.can_attack = True
        self.dash_length = 30
        super().__init__(x, y, data["img"], data["hp"], data["armor"], data["protection"], data["walk_speed"],
                         data["run_speed"], data["attack_cooldown"], data["damage"], 'SwordMan')
        self.gun = Sword(x, y, self.damage, self.team, self)
        self.can_attack_timer = None

    def enable_attack(self):
        self.can_attack = True

    def attack(self, x, y):
        self.running = False
        if self.can_attack:
            self.gun.attack()
            self.can_attack = False
            self.can_attack_timer = Timer(self.attack_cooldown, self.enable_attack).start()

    def look_at_mouse(self):
        if not self.gun.attacking:
            x, y = from_local_to_global_pos(*pygame.mouse.get_pos())
            self.gun.angle = pygame.Vector2(x - self.global_x - self.gun.rect.w // 2, y - self.global_y
                                            - self.gun.rect.h // 2).normalize().angle_to(pygame.Vector2(1, 0))
            if self.gun.angle < 0:
                self.gun.angle += 360
            self.gun.image = pygame.transform.rotate(self.gun.orig_image, self.gun.angle)
            self.gun.set_pos(self.global_x + 40 * math.cos(self.gun.angle / 180 * math.pi) + 3,
                             self.global_y - 40 * math.sin(self.gun.angle / 180 * math.pi) + 15)

    def die(self):
        if self.can_attack_timer:
            self.can_attack_timer.cancel()
        if self.gun:
            self.gun.die()
        super().die()


class Sword(BaseGameObject):
    def __init__(self, x, y, damage, team, parent):
        self.damage = damage
        self.parent = parent
        self.damage_taken = []
        self.attacking = False
        self.angle = 0
        self.vector = pygame.Vector2(0, 0)
        super().__init__(x - 50, y - 20, units_characteristics.swordman["gun_img"], HITBOX_ARROW, team, True)
        self.hitbox.can_slide = False
        self.orig_image = self.image
        all_sprites.change_layer(self, 0)

    def attack(self):
        self.vector = pygame.Vector2(1, 0).rotate(-self.angle).normalize()
        self.attacking = True
        Timer(0.05, self.attacking_false).start()

    def attacking_false(self):
        self.attacking = False
        self.damage_taken.clear()
        self.vector = pygame.Vector2(0, 0)

    def update(self):
        all_sprites.change_layer(self, self.hitbox.rect.bottom)
        if self.attacking:
            self.global_x += self.vector.x * 10
            self.global_y += self.vector.y * 10
            for i in self.hitbox.get_colliding_objects():
                if i not in self.damage_taken:
                    if pygame.sprite.collide_mask(self.hitbox, i):
                        if hasattr(i.parent, "hp"):
                            i.parent.take_damage(self.damage)
                            self.parent.heal(self.damage * self.parent.vampirism)
                            if self.parent.candle_damage:
                                Timer(1, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                                Timer(2, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                                Timer(3, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                                Timer(4, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                                Timer(5, i.parent.take_damage, [self.parent.candle_damage, True]).start()
                        self.damage_taken.append(i)
        self.hitbox.set_pos(self.global_x, self.global_y)
        super().update()
