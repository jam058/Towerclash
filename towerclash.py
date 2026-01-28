import pygame
import json
import os
import random
import math
from collections import deque
import sys

# pygame-ce should be installed → pip install pygame-ce

pygame.init()
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Tower Clash - Visual Battles!")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 48)
med_font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_BG = (20, 20, 40)
GRAY = (128, 128, 128)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (100, 150, 255)
ORANGE = (255, 150, 0)
PURPLE = (200, 100, 255)
YELLOW = (255, 255, 0)

SAVE_FILE = 'save.json'

card_data = {
    'Basic Warrior': {'hp': 150, 'atk': 30, 'ability': 'none', 'color': GRAY},
    'Basic Mage': {'hp': 100, 'atk': 40, 'ability': 'none', 'color': BLUE},
    'Flame Tyrant': {'hp': 200, 'atk': 35, 'ability': 'burn_aoe', 'color': ORANGE},
    'Crimson Vampire': {'hp': 250, 'atk': 25, 'ability': 'revive', 'color': RED},
    'Awakened Shadow Monarch': {'hp': 400, 'atk': 60, 'ability': 'counter', 'color': PURPLE},
    'Berserker Shinigami': {'hp': 300, 'atk': 40, 'ability': 'revive', 'color': (200, 0, 0)},
    'Awakened Sun Deity': {'hp': 500, 'atk': 70, 'ability': 'scale_dmg', 'color': YELLOW},
    'Eternal Mage': {'hp': 350, 'atk': 50, 'ability': 'steal', 'color': (150, 100, 255)}
}

card_colors = {name: data['color'] for name, data in card_data.items()}

class VisualCard:
    def __init__(self, name, scale=1.0, side='player'):
        data = card_data[name]
        self.name = name
        self.max_hp = data['hp'] * scale
        self.hp = self.max_hp
        self.atk = data['atk'] * scale
        self.ability = data['ability']
        self.side = side
        self.alive = True
        self.slot = 0
        self.pos = [0, 0]
        self.shake_offset = [0, 0]
        self.dmg_pops = []  # (text, timer, dy)
        self.burn_dmg = 0.0
        self.entry_done = False
        self.dmg_mult = 1.0
        self.revives_used = 0
        self.has_stolen = False
        self.revive_timer = 0.0
        self.death_timer = 0.0
        self.time = 0.0
        # self.image = pygame.image.load(f"assets/{name.lower().replace(' ', '_')}.png")  # uncomment when you add images

    def update(self, dt):
        self.time += dt
        self.shake_offset[0] *= 0.85
        self.shake_offset[1] *= 0.85
        self.revive_timer = max(0, self.revive_timer - dt)
        self.death_timer = min(2.0, self.death_timer + dt)
        self.dmg_pops = [(txt, t - dt, dy + 60 * dt) for txt, t, dy in self.dmg_pops if t > 0]

    def take_damage(self, dmg, attacker=None):
        prev_hp = self.hp
        self.hp -= dmg
        self.dmg_pops.append((f"-{int(dmg)}", 1.5, 0))
        self.shake_offset = [random.uniform(-15, 15), random.uniform(-10, 10)]
        if self.hp <= 0 and prev_hp > 0:
            revived = False
            if self.ability == 'revive' and self.revives_used < 1:
                self.revives_used += 1
                self.hp = self.max_hp * 0.5
                self.revive_timer = 1.0
                revived = True
            if not revived:
                self.alive = False
                self.death_timer = 0.0
        self.hp = max(0, self.hp)
        self.alive = self.hp > 0

    def compute_dmg(self, turn):
        mult = self.dmg_mult
        if self.ability == 'counter' and turn % 2 == 0:
            mult *= 1.75
        return self.atk * mult

    def attack(self, target, turn, action_log):
        if not self.alive or not target.alive:
            return
        dmg = self.compute_dmg(turn)
        if self.ability == 'steal' and not self.has_stolen:
            self.has_stolen = True
            self.atk *= 1.5
            action_log.append(f"{self.name} steals power!")
        target.take_damage(dmg)
        action_log.append(f"{self.name} attacks {target.name} for {int(dmg)}!")

    def apply_entry(self, enemies, action_log):
        if self.ability == 'burn_aoe' and not self.entry_done and self.alive:
            self.entry_done = True
            for enemy in enemies:
                enemy.burn_dmg = 0.15 * enemy.max_hp
            action_log.append(f"{self.name} ignites all enemies!")

    def draw(self, screen):
        x, y = self.pos[0] + self.shake_offset[0], self.pos[1] + self.shake_offset[1]
        color = card_colors.get(self.name, GRAY)
        pygame.draw.rect(screen, color, (x - 50, y - 100, 100, 200), border_radius=12)
        pygame.draw.rect(screen, WHITE, (x - 50, y - 100, 100, 200), 3, border_radius=12)
        # Placeholder circle for card art
        pygame.draw.circle(screen, (255, 220, 180), (int(x), int(y - 20)), 35)
        name_surf = small_font.render(self.name, True, BLACK)
        screen.blit(name_surf, (x - name_surf.get_width() // 2, y + 70))
        # HP bar
        bar_x, bar_y = x - 40, y + 35
        bar_w, bar_h = 80, 12
        fill_w = (self.hp / self.max_hp) * bar_w if self.max_hp > 0 else 0
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(screen, BLACK, (bar_x, bar_y, bar_w, bar_h), 2)
        # Ability label
        ab_surf = small_font.render(self.ability[:4].upper(), True, WHITE)
        screen.blit(ab_surf, (x - ab_surf.get_width() // 2, y - 85))
        # Damage popups
        for txt, t, dy in self.dmg_pops:
            col = YELLOW if t > 0.7 else RED
            surf = small_font.render(txt, True, col)
            screen.blit(surf, (x - surf.get_width() // 2, y - 20 - dy))
        # Burn overlay
        if self.burn_dmg > 0:
            alpha = int(40 + 30 * abs(math.sin(self.time * 8)))
            overlay = pygame.Surface((110, 210), pygame.SRCALPHA)
            overlay.fill((*RED, alpha))
            screen.blit(overlay, (x - 55, y - 105))
        # Revive flash
        if self.revive_timer > 0:
            alpha = int(80 * self.revive_timer)
            overlay = pygame.Surface((110, 210), pygame.SRCALPHA)
            overlay.fill((*GREEN, alpha))
            screen.blit(overlay, (x - 55, y - 105))
        # Dead overlay
        if not self.alive:
            overlay = pygame.Surface((110, 210), pygame.SRCALPHA)
            overlay.fill((GRAY, 120))
            screen.blit(overlay, (x - 55, y - 105))

def load_save():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault('unlocked', ['Basic Warrior', 'Basic Mage'])
            data.setdefault('deck', ['Basic Warrior'] * 4)
            data.setdefault('progress', {'tower1': 0, 'tower2': -1, 'tower3': -1})
            return data
    return {
        'unlocked': ['Basic Warrior', 'Basic Mage'],
        'deck': ['Basic Warrior'] * 4,
        'progress': {'tower1': 0, 'tower2': -1, 'tower3': -1}
    }

def save_game(data):
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f)

towers = {
    'tower1': {
        'name': 'Flame Depths', 'floors': 5,
        'unlock': ['Flame Tyrant', 'Crimson Vampire'],
        'enemies': [
            ['Basic Warrior'],
            ['Basic Warrior', 'Basic Mage'],
            ['Basic Mage', 'Basic Mage'],
            ['Basic Warrior', 'Basic Warrior'],
            ['Basic Warrior', 'Basic Mage', 'Basic Mage']
        ]
    },
    'tower2': {
        'name': 'Shadow Citadel', 'floors': 5,
        'unlock': ['Awakened Shadow Monarch', 'Berserker Shinigami'],
        'enemies': [
            ['Flame Tyrant'],
            ['Crimson Vampire', 'Basic Warrior'],
            ['Flame Tyrant', 'Flame Tyrant'],
            ['Crimson Vampire', 'Crimson Vampire'],
            ['Flame Tyrant', 'Crimson Vampire', 'Flame Tyrant']
        ]
    },
    'tower3': {
        'name': 'Celestial Peak', 'floors': 5,
        'unlock': ['Awakened Sun Deity', 'Eternal Mage'],
        'enemies': [
            ['Awakened Shadow Monarch'],
            ['Berserker Shinigami', 'Flame Tyrant'],
            ['Awakened Shadow Monarch', 'Crimson Vampire'],
            ['Berserker Shinigami', 'Berserker Shinigami'],
            ['Awakened Shadow Monarch', 'Berserker Shinigami', 'Flame Tyrant', 'Crimson Vampire']
        ]
    }
}

def run_battle(p_deck_names, e_deck_names, scale=1.0):
    # Clean decks
    p_deck_names = [n for n in p_deck_names if isinstance(n, str) and n in card_data]
    e_deck_names = [n for n in e_deck_names if isinstance(n, str) and n in card_data]

    if not p_deck_names or not e_deck_names:
        print("Skipping battle: empty or invalid deck")
        return False

    p_cards = [VisualCard(name, scale, 'player') for name in p_deck_names]
    e_cards = [VisualCard(name, scale, 'enemy') for name in e_deck_names]

    # Positions
    player_x = 220
    enemy_x = 920
    y_start = 160
    spacing = 95
    for i, card in enumerate(p_cards):
        card.pos = [player_x, y_start + i * spacing]
        card.slot = i
    for i, card in enumerate(e_cards):
        card.pos = [enemy_x, y_start + i * spacing]
        card.slot = i

    turn = 0
    action_phase = 'status'
    action_log = deque(maxlen=10)
    next_action_time = 0
    battle_end_timer = 0
    end_victory = False
    current_time = 0
    fast_forward = False

    while True:
        dt = clock.tick(60) / 1000.0
        current_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    fast_forward = True
                if event.key == pygame.K_ESCAPE:
                    return False

        if fast_forward:
            next_action_time = current_time
            fast_forward = False

        for card in p_cards + e_cards:
            card.update(dt)

        if current_time >= next_action_time and battle_end_timer == 0:
            next_action_time = current_time + 0.8

            if action_phase == 'status':
                for card in p_cards + e_cards:
                    if card.alive and card.burn_dmg > 0:
                        bdmg = card.burn_dmg
                        card.take_damage(bdmg)
                        action_log.append(f"{card.name} burns for {int(bdmg)}!")
                for card in p_cards:
                    card.apply_entry([c for c in e_cards if c.alive], action_log)
                for card in e_cards:
                    card.apply_entry([c for c in p_cards if c.alive], action_log)
                action_phase = 'player'

            elif action_phase == 'player':
                alive_p = [c for c in p_cards if c.alive]
                alive_e = [c for c in e_cards if c.alive]
                if alive_p and alive_e:
                    attacker = min(alive_p, key=lambda c: c.slot)
                    target = min(alive_e, key=lambda c: c.slot)
                    attacker.attack(target, turn, action_log)
                action_phase = 'enemy'

            elif action_phase == 'enemy':
                alive_e = [c for c in e_cards if c.alive]
                alive_p = [c for c in p_cards if c.alive]
                if alive_e and alive_p:
                    attacker = min(alive_e, key=lambda c: c.slot)
                    target = min(alive_p, key=lambda c: c.slot)
                    attacker.attack(target, turn, action_log)
                action_phase = 'status'
                turn += 1

            p_alive = any(c.alive for c in p_cards)
            e_alive = any(c.alive for c in e_cards)
            if not e_alive:
                battle_end_timer = current_time + 3.0
                end_victory = True
            elif not p_alive:
                battle_end_timer = current_time + 3.0
                end_victory = False

        elif battle_end_timer > 0 and current_time >= battle_end_timer:
            return end_victory

        # Drawing code (same as before)
        screen.fill(DARK_BG)
        p_title = med_font.render("Your Party", True, WHITE)
        screen.blit(p_title, (50, 50))
        e_title = med_font.render("Enemies", True, WHITE)
        screen.blit(e_title, (SCREEN_WIDTH - 250, 50))
        turn_surf = font.render(f"Turn {turn}", True, YELLOW)
        screen.blit(turn_surf, (SCREEN_WIDTH // 2 - turn_surf.get_width() // 2, 20))
        pygame.draw.line(screen, WHITE, (580, 100), (580, SCREEN_HEIGHT - 150), 4)

        for card in p_cards + e_cards:
            card.draw(screen)

        p_total = sum(c.hp for c in p_cards if c.alive)
        e_total = sum(c.hp for c in e_cards if c.alive)
        screen.blit(med_font.render(f"Your HP: {int(p_total)}", True, GREEN), (50, SCREEN_HEIGHT - 60))
        screen.blit(med_font.render(f"Enemy HP: {int(e_total)}", True, RED), (SCREEN_WIDTH - 300, SCREEN_HEIGHT - 60))

        log_y = SCREEN_HEIGHT - 150
        for i, log_txt in enumerate(list(action_log)):
            log_surf = small_font.render(log_txt, True, WHITE)
            screen.blit(log_surf, (50, log_y - i * 22))

        if battle_end_timer > 0:
            alpha = int(200 * (1 - (current_time - (battle_end_timer - 3)) / 3))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            screen.blit(overlay, (0, 0))
            end_text = font.render("VICTORY!" if end_victory else "DEFEAT!", True, GREEN if end_victory else RED)
            screen.blit(end_text, (SCREEN_WIDTH // 2 - end_text.get_width() // 2, SCREEN_HEIGHT // 2 - end_text.get_height() // 2))
            cont_text = small_font.render("ESC to return", True, WHITE)
            screen.blit(cont_text, (SCREEN_WIDTH // 2 - cont_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

        pygame.display.flip()

def main():
    data = load_save()
    state = 'main_menu'
    selected_slot = -1
    custom_enemy_deck = [None] * 4
    back_button_rect = pygame.Rect(50, 50, 200, 60)
    done_button_rect = pygame.Rect(SCREEN_WIDTH - 300, SCREEN_HEIGHT - 100, 250, 60)

    while True:
        dt = clock.tick(60) / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game(data)
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        screen.fill(DARK_BG)

        if state == 'main_menu':
            buttons = [
                (pygame.Rect(100, 150, 400, 70), "View Unlocked"),
                (pygame.Rect(100, 250, 400, 70), "Build Deck"),
                (pygame.Rect(100, 350, 400, 70), "Climb Tower"),
                (pygame.Rect(100, 450, 400, 70), "Custom Battle"),
                (pygame.Rect(100, 550, 400, 70), "Quit")
            ]
            for rect, text in buttons:
                color = BLUE if rect.collidepoint(mouse_pos) else (50, 50, 150) if text != "Quit" else RED
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, WHITE, rect, 3)
                txt_surf = med_font.render(text, True, WHITE)
                screen.blit(txt_surf, (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2))

            if clicked:
                for rect, text in buttons:
                    if rect.collidepoint(mouse_pos):
                        if text == "Quit":
                            save_game(data)
                            pygame.quit()
                            sys.exit()
                        elif text == "View Unlocked":
                            state = 'view_unlocked'
                        elif text == "Build Deck":
                            state = 'build_deck'
                        elif text == "Climb Tower":
                            state = 'tower_select'
                        elif text == "Custom Battle":
                            state = 'custom_build'

        elif state in ['build_deck', 'custom_build']:
            is_custom = state == 'custom_build'
            target_deck = custom_enemy_deck if is_custom else data['deck']
            deck_name = "Enemy Deck (Custom)" if is_custom else "Your Deck"

            y = 150
            deck_slots_rects = []
            for i in range(4):
                rect = pygame.Rect(100, y + i * 70, 500, 60)
                deck_slots_rects.append((i, rect))
                color = BLUE if rect.collidepoint(mouse_pos) else DARK_BG
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, WHITE, rect, 3)
                name = target_deck[i] if target_deck[i] else "Empty"
                txt = med_font.render(f"Slot {i+1}: {name}", True, WHITE)
                screen.blit(txt, (rect.x + 10, rect.y + 15))
                if i == selected_slot:
                    pygame.draw.rect(screen, YELLOW, rect, 5)

            y = 150
            unlocked_rects = []
            for card in sorted(set(data['unlocked'])):
                rect = pygame.Rect(650, y, 500, 50)
                unlocked_rects.append((card, rect))
                color = card_colors.get(card, GRAY)
                pygame.draw.rect(screen, color if not rect.collidepoint(mouse_pos) else (*color, 220), rect)
                pygame.draw.rect(screen, WHITE, rect, 2)
                txt = small_font.render(card, True, BLACK)
                screen.blit(txt, (660, y + 15))
                y += 55

            pygame.draw.rect(screen, GREEN, done_button_rect)
            pygame.draw.rect(screen, WHITE, done_button_rect, 3)
            done_txt = med_font.render("Done" if not is_custom else "Battle!", True, WHITE)
            screen.blit(done_txt, (done_button_rect.centerx - done_txt.get_width() // 2, done_button_rect.centery - done_txt.get_height() // 2))

            pygame.draw.rect(screen, BLUE, back_button_rect)
            back_txt = med_font.render("Back", True, WHITE)
            screen.blit(back_txt, (back_button_rect.centerx - back_txt.get_width() // 2, back_button_rect.centery - back_txt.get_height() // 2))

            title_txt = font.render(deck_name, True, WHITE)
            screen.blit(title_txt, (SCREEN_WIDTH // 2 - title_txt.get_width() // 2, 50))

            if clicked:
                for i, rect in deck_slots_rects:
                    if rect.collidepoint(mouse_pos):
                        selected_slot = i
                        break
                else:
                    selected_slot = -1

                if selected_slot != -1:
                    for card, rect in unlocked_rects:
                        if rect.collidepoint(mouse_pos):
                            target_deck[selected_slot] = card
                            selected_slot = -1
                            break

                if done_button_rect.collidepoint(mouse_pos):
                    if is_custom:
                        valid_deck = [d for d in custom_enemy_deck if d]
                        if valid_deck:
                            win = run_battle(data['deck'], valid_deck, 1.0)
                            print(f"Custom Battle: {'Win!' if win else 'Loss!'}")
                    else:
                        save_game(data)
                    state = 'main_menu'
                elif back_button_rect.collidepoint(mouse_pos):
                    state = 'main_menu'
                    if is_custom:
                        custom_enemy_deck = [None] * 4

        elif state == 'view_unlocked':
            y = 150
            for card in sorted(set(data['unlocked'])):
                color = card_colors.get(card, GRAY)
                rect = pygame.Rect(100, y, 500, 50)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, WHITE, rect, 2)
                txt = small_font.render(card, True, BLACK)
                screen.blit(txt, (110, y + 15))
                y += 60
            pygame.draw.rect(screen, BLUE, back_button_rect)
            txt = med_font.render("Back", True, WHITE)
            screen.blit(txt, (back_button_rect.centerx - txt.get_width() // 2, back_button_rect.centery - txt.get_height() // 2))
            if clicked and back_button_rect.collidepoint(mouse_pos):
                state = 'main_menu'

        elif state == 'tower_select':
            y = 200
            tower_buttons = []
            for tkey in ['tower1', 'tower2', 'tower3']:
                prog = data['progress'][tkey]
                if prog < 0:
                    continue
                rect = pygame.Rect(200, y, 800, 80)
                tower_buttons.append((tkey, rect))
                color = ORANGE if rect.collidepoint(mouse_pos) else (100, 50, 0)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, WHITE, rect, 4)
                name = towers[tkey]['name']
                floor = prog + 1
                txt = font.render(f"{name} - Floor {floor}/{towers[tkey]['floors']}", True, WHITE)
                screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
                y += 100

            pygame.draw.rect(screen, BLUE, back_button_rect)
            txt = med_font.render("Back", True, WHITE)
            screen.blit(txt, (back_button_rect.centerx - txt.get_width() // 2, back_button_rect.centery - txt.get_height() // 2))

            if clicked:
                for tkey, rect in tower_buttons:
                    if rect.collidepoint(mouse_pos):
                        current_tower = tkey
                        floor = data['progress'][tkey]
                        scale = 1.0 + 0.3 * floor
                        enemy_deck = towers[tkey]['enemies'][floor]
                        enemy_deck = [card for sublist in enemy_deck for card in sublist]  # flatten
                        win = run_battle(data['deck'], enemy_deck, scale)
                        if win:
                            data['progress'][tkey] += 1
                            if data['progress'][tkey] == towers[tkey]['floors']:
                                data['unlocked'].extend(towers[tkey]['unlock'])
                                data['unlocked'] = list(set(data['unlocked']))
                                print(f"TOWER CLEARED! Unlocked: {towers[tkey]['unlock']}")
                                if tkey == 'tower1':
                                    data['progress']['tower2'] = 0
                                elif tkey == 'tower2':
                                    data['progress']['tower3'] = 0
                            save_game(data)
                        state = 'main_menu'
                        break
                if back_button_rect.collidepoint(mouse_pos):
                    state = 'main_menu'

        pygame.display.flip()

if __name__ == "__main__":
    main()