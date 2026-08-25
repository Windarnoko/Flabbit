import sys
import random
import pygame
import asyncio
from pygame.locals import *

pygame.init()

mixer_available = True
try:
    pygame.mixer.init()
except Exception:
    mixer_available = False

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 800
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird-like Game with Shooting and Enemies")

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)

player_image = pygame.image.load('asset/bluebird-downflap.webp').convert_alpha()
character_rect = player_image.get_rect() 

gameover_image = pygame.image.load('asset/gameover.webp').convert_alpha()
gameover_rect = gameover_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)) 

congratulation_image = pygame.image.load('asset/congratulation.webp').convert_alpha()
congratulation_rect = congratulation_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

character_x = SCREEN_WIDTH // 2
character_y = SCREEN_HEIGHT // 2
character_speed = 5

max_health = 100
health = max_health 
score = 0
invincible = False
invincible_timer = 0
blink_timer = 0

# tembok (ubah warna ke hijau)
walls = [
    pygame.Rect(SCREEN_WIDTH, 0, 50, 300),    
    pygame.Rect(SCREEN_WIDTH, 500, 50, 300), 
]
wall_speed = 3  

# Peluru (ubah menjadi laser dengan damage 10)
bullets = []
bullet_speed = 7
bullet_damage = 10  # Damage laser

# Enemy
enemies = []
enemy_speed = 2  
enemy_spawn_timer = 0  
enemy_image = pygame.image.load('asset/redbird-upflap.webp').convert_alpha()

# Boss variables
boss_active = False
boss_image = pygame.transform.scale(player_image, (player_image.get_width() * 3, player_image.get_height() * 3))  # Boss 3x ukuran player
boss_rect = boss_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
boss_health = max_health * 2  # 200
boss_max_health = boss_health

# Victory flag
victory = False

# Font untuk teks health dan score
font = pygame.font.Font(None, 36)

# Audio helpers: try .ogg then .mp3; if loading fails return a dummy sound with play() no-op
class _DummySound:
    def play(self, *_, **__):
        return None


def _load_sound(base_path_without_ext):
    """Attempt to load base_path_without_ext + .ogg, then .mp3. Return a Sound or a dummy object."""
    if not mixer_available:
        return _DummySound()
    for ext in ('.ogg', '.mp3'):
        path = base_path_without_ext + ext
        try:
            return pygame.mixer.Sound(path)
        except Exception:
            continue
    return _DummySound()


def _load_music(base_path_without_ext):
    """Attempt to load music: prefer .ogg then .mp3. Return True if loaded."""
    if not mixer_available:
        return False
    for ext in ('.ogg', '.mp3'):
        path = base_path_without_ext + ext
        try:
            pygame.mixer.music.load(path)
            return True
        except Exception:
            continue
    return False

# Load suara (graceful fallback if files are missing or unsupported)
hit_sound = _load_sound('asset/hit')
kill_sound = _load_sound('asset/kill')
shoot_sound = _load_sound('asset/shoot')
start_sound = _load_sound('asset/start')
gameover_sound = _load_sound('asset/gameover')

# Load backsound (musik latar) — prefer OGG if present
_music_loaded = _load_music('asset/backsound')

# Mainkan suara start dan mulai backsound if available
try:
    if hasattr(start_sound, 'play'):
        start_sound.play()
    if _music_loaded:
        pygame.mixer.music.play(-1)
except Exception:
    # Silently ignore audio playback errors
    pass

# Loop game utama
async def wait_next_frame():
    await asyncio.sleep(1 / 60)


async def main():
    global character_x, character_y, health, score, invincible, invincible_timer, blink_timer
    global walls, bullets, enemies, enemy_spawn_timer, boss_active, boss_health, victory

    running = True
    game_over = False
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over:
                    bullet_rect = pygame.Rect(character_x + player_image.get_width(), character_y + player_image.get_height() // 2 - 5, 20, 5)
                    bullets.append(bullet_rect)
                    shoot_sound.play()

                elif event.key == pygame.K_r and game_over:
                    health = max_health
                    score = 0
                    invincible = False
                    invincible_timer = 0
                    blink_timer = 0
                    character_x = SCREEN_WIDTH // 2
                    character_y = SCREEN_HEIGHT // 2
                    bullets.clear()
                    enemies.clear()
                    walls = [
                        pygame.Rect(SCREEN_WIDTH, 0, 50, 300),
                        pygame.Rect(SCREEN_WIDTH, 500, 50, 300),
                    ]
                    boss_active = False
                    boss_health = boss_max_health
                    victory = False
                    game_over = False
                    pygame.mixer.music.play(-1)
                elif event.key == pygame.K_q and game_over:
                    running = False

        if not game_over:
            old_x, old_y = character_x, character_y

            keys = pygame.key.get_pressed()
            if keys[pygame.K_a]:
                character_x -= character_speed
            if keys[pygame.K_d]:
                character_x += character_speed
            if keys[pygame.K_w]:
                character_y -= character_speed
            if keys[pygame.K_s]:
                character_y += character_speed

            character_rect.topleft = (character_x, character_y)

            character_x = max(0, min(character_x, SCREEN_WIDTH - player_image.get_width()))
            character_y = max(0, min(character_y, SCREEN_HEIGHT - player_image.get_height()))

            # Update invincibility (5 detik)
            if invincible:
                invincible_timer -= 1
                blink_timer += 1
                if invincible_timer <= 0:
                    invincible = False
                    blink_timer = 0

            for wall in walls:
                wall.x -= wall_speed

            if walls[0].x + walls[0].width < 0:
                top_height = random.randint(100, 400)
                gap = random.randint(150, 250)
                bottom_height = SCREEN_HEIGHT - top_height - gap

                walls[0] = pygame.Rect(SCREEN_WIDTH, 0, 50, top_height)
                walls[1] = pygame.Rect(SCREEN_WIDTH, top_height + gap, 50, bottom_height)

            for bullet in bullets[:]:
                bullet.x += bullet_speed
                if bullet.x > SCREEN_WIDTH:
                    bullets.remove(bullet)

            # Spawn enemy hanya jika score < 30 dan boss tidak aktif
            if score < 30 and not boss_active:
                enemy_spawn_timer += 1
                if enemy_spawn_timer > 120:
                    enemy_y = random.randint(50, SCREEN_HEIGHT - 50)
                    enemy_rect = pygame.Rect(SCREEN_WIDTH, enemy_y, 30, 30)
                    enemies.append(enemy_rect)
                    enemy_spawn_timer = 0

            # Gerakkan enemy ke kiri
            for enemy in enemies[:]:
                enemy.x -= enemy_speed
                if enemy.x + enemy.width < 0:
                    enemies.remove(enemy)

            # Deteksi tabrakan peluru dengan enemy atau boss
            for bullet in bullets[:]:
                if boss_active:
                    if bullet.colliderect(boss_rect):
                        bullets.remove(bullet)
                        boss_health -= bullet_damage
                        if boss_health <= 0:
                            victory = True
                            game_over = True
                            pygame.mixer.music.stop()
                        break
                else:
                    for enemy in enemies[:]:
                        if bullet.colliderect(enemy):
                            bullets.remove(bullet)
                            enemies.remove(enemy)
                            score += 1
                            kill_sound.play()
                            break

            # Cek jika score mencapai 30, aktifkan boss
            if score >= 30 and not boss_active:
                boss_active = True
                enemies.clear()

            hit_wall = False
            hit_enemy = False
            hit_boss = False
            for wall in walls:
                if character_rect.colliderect(wall):
                    hit_wall = True
                    break
            for enemy in enemies:
                if character_rect.colliderect(enemy):
                    hit_enemy = True
                    enemies.remove(enemy)
                    break
            if boss_active and character_rect.colliderect(boss_rect):
                hit_boss = True

            if hit_wall and not invincible:
                health -= 20
                hit_sound.play()
                invincible = True
                invincible_timer = 300
                character_x, character_y = old_x, old_y

            if hit_enemy:
                health -= 10
                hit_sound.play()
                character_x, character_y = old_x, old_y

            if hit_boss and not invincible:
                health -= 20
                hit_sound.play()
                invincible = True
                invincible_timer = 300
                character_x, character_y = old_x, old_y

            if health <= 0:
                game_over = True
                pygame.mixer.music.stop()
                gameover_sound.play()

        # Background: hitam saat game_over, else putih jika score < 30, hitam jika >= 30
        if game_over:
            screen.fill(BLACK)
        elif score >= 30:
            screen.fill(BLACK)
        else:
            screen.fill(WHITE)

        if game_over:
            if victory:
                screen.blit(congratulation_image, congratulation_rect)
            else:
                screen.blit(gameover_image, gameover_rect)
            restart_text = font.render("Press R to Restart or Q to Quit", True, (255, 255, 255))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 100))
        else:
            # Gambar tembok (pipes): hijau jika score < 30, merah jika >= 30
            pipe_color = GREEN if score < 30 else RED
            for wall in walls:
                pygame.draw.rect(screen, pipe_color, wall)

            # Gambar enemy hanya jika score < 30
            if score < 30:
                for enemy in enemies:
                    scaled_enemy = pygame.transform.scale(enemy_image, (enemy.width, enemy.height))
                    screen.blit(scaled_enemy, enemy.topleft)

            # Gambar boss jika aktif
            if boss_active:
                screen.blit(boss_image, boss_rect.topleft)
                # Health bar boss
                pygame.draw.rect(screen, RED, (boss_rect.centerx - 100, boss_rect.bottom + 10, 200, 20))
                pygame.draw.rect(screen, GREEN, (boss_rect.centerx - 100, boss_rect.bottom + 10, 200 * (boss_health / boss_max_health), 20))
                boss_health_text = font.render(f"Boss Health: {boss_health}", True, (255, 255, 255))
                screen.blit(boss_health_text, (boss_rect.centerx - 100, boss_rect.bottom + 35))

            # Gambar peluru (laser merah)
            for bullet in bullets:
                pygame.draw.rect(screen, RED, bullet)

            # Gambar player (burung) dengan blink jika invincible
            if not invincible or (blink_timer // 10) % 2 == 0:
                screen.blit(player_image, (character_x, character_y))

            # Tentukan warna font: hitam jika score < 30, putih jika >= 30
            text_color = BLACK if score < 30 else WHITE

            # Gambar health bar
            pygame.draw.rect(screen, RED, (10, 10, 200, 20))
            pygame.draw.rect(screen, GREEN, (10, 10, 200 * (health / max_health), 20))
            health_text = font.render(f"Health: {health}", True, text_color)
            screen.blit(health_text, (10, 40))

            # Gambar skor
            score_text = font.render(f"Score: {score}", True, text_color)
            screen.blit(score_text, (10, 70))

        pygame.display.flip()
        await wait_next_frame()

    pygame.quit()
    sys.exit()


asyncio.run(main())