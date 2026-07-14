import math
import os
import random
import sys
import time
import pygame as pg

WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx - org.centerx, dst.centery - org.centery
    norm = math.sqrt(x_diff**2 + y_diff**2)
    if norm == 0:
        norm = 1
    return x_diff / norm, y_diff / norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """

    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface, score: "Score"):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        引数3 score：スコア管理オブジェクト
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed * sum_mv[0], self.speed * sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed * sum_mv[0], -self.speed * sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
        if self.state == "hyper":
            self.hyper_life -= 1
            self.image = pg.transform.laplacian(self.imgs[self.dire])
            if self.hyper_life < 0:
                self.state = "normal"
                self.image = self.imgs[self.dire]
        else:
            self.image = self.imgs[self.dire]
            if key_lst[pg.K_RSHIFT] and score.value > 100:
                self.state = "hyper"
                self.hyper_life = 500
                score.value -= 100
                self.image = pg.transform.laplacian(self.imgs[self.dire])
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """

    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2 * rad, 2 * rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery + emy.rect.height // 2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """

    def __init__(self, bird: Bird, angle_offset: float = 0.0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        引数 angle_offset：ビームの角度オフセット
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx)) + angle_offset
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        """
        self.rect.move_ip(self.speed * self.vx, self.speed * self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """

    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life // 10 % 2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """

    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT // 2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Boss(Enemy):
    """
    ボスに関するクラス
    """

    def __init__(self):
        super().__init__()
        # ボス画像を読み込み、やや大きめに表示
        try:
            img = pg.transform.rotozoom(pg.image.load(f"fig/boss.png"), 0, 1.0)
        except Exception:
            img = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 1.0)
        self.image = img
        self.rect = self.image.get_rect()
        # 画面上部中央に出現
        self.rect.center = (WIDTH // 2, 80)
        self.vx = 6  # 横移動速度
        self.vy = 0
        self.state = "active"

        # 体力
        self.hp = 100

        # 発射パターン管理（フレーム単位、50fps前提）
        self.in_burst = True
        self.shots_fired = 0
        self.shot_frame_interval = 10  # 5発/秒 -> 0.2sごと -> 10フレーム
        self.shot_frame_count = 0
        self.pause_frames = 50  # 1秒間の待機 -> 50フレーム
        self.pause_count = 0

    def update(self):
        # 左右に移動して画面端で反転
        self.rect.move_ip(self.vx, 0)
        if self.rect.left < 0 or self.rect.right > WIDTH:
            self.vx = -self.vx
            self.rect.move_ip(self.vx, 0)


class Life:
    def __init__(self, num):
        self.num = num
        self.image = pg.Surface((40, 40), pg.SRCALPHA)

        pg.draw.circle(self.image, (255, 0, 0), (12, 12), 8)
        pg.draw.circle(self.image, (255, 0, 0), (28, 12), 8)
        pg.draw.polygon(self.image, (255, 0, 0), [(4, 16), (20, 36), (36, 16)])

    def update(self, screen):
        for i in range(self.num):
            rect = self.image.get_rect()
            rect.center = (WIDTH - 50 - i * 45, HEIGHT - 50)
            screen.blit(self.image, rect)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """

    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT - 50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP:
    """
    電磁パルス（EMP）に関するクラス
    """

    def __init__(
        self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface, exps: pg.sprite.Group, score: "Score"
    ):
        emp_surf = pg.Surface((WIDTH, HEIGHT))  # 画面を黄色に
        emp_surf.set_alpha(128)  # 半透明に
        emp_surf.fill((255, 255, 0))
        screen.blit(emp_surf, (0, 0))
        pg.display.update()
        time.sleep(0.05)

        # 敵機の無効化
        for emy in list(emys):
            emy.interval = float("inf")  # 爆弾投下できない
            try:
                emy.image = pg.transform.laplacian(emy.image)
            except:
                pass
            # ボスがいればダメージを与える
            if isinstance(emy, Boss):
                emy.hp -= 10
                if emy.hp <= 0:
                    exps.add(Explosion(emy, 100))
                    score.value += 10
                    emy.kill()

        for bomb in bombs:  # 爆弾無効化
            bomb.speed *= 0.5
            bomb.state = "inactive"


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """

    def __init__(self, life):
        super().__init__()

        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image, (0, 0, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 半透明
        self.rect = self.image.get_rect()

        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


class BulletCount:
    """
    残弾数を表示するクラス
    """

    def __init__(self, init_bullets=5):
        self.value = init_bullets

        raw_img = pg.image.load("fig/bullet.png")
        self.bullet_img = pg.transform.scale(raw_img, (50, 50))

        self.font = pg.font.Font(None, 40)
        self.color = (0, 0, 0)

    def update(self, screen):
        img_rect = self.bullet_img.get_rect()
        img_rect.right = WIDTH - 230
        img_rect.centery = HEIGHT - 50
        screen.blit(self.bullet_img, img_rect)

        txt = self.font.render(f"x {self.value}", True, self.color)
        txt_rect = txt.get_rect()
        txt_rect.left = img_rect.right + 8
        txt_rect.centery = HEIGHT - 50
        screen.blit(txt, txt_rect)


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life = Life(3)
    bullets = BulletCount(5)  # 初期弾数5
    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    gravities = pg.sprite.Group()
    enemy_kill_count = 0

    tmr = 0
    clock = pg.time.Clock()

    charge_cnt = 0

    while True:
        # ★バグ修正①: 画面の更新用背景描画をループの先頭に配置
        screen.blit(bg_img, [0, 0])

        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if bullets.value > 0:
                    beams.add(Beam(bird))
                    bullets.value -= 1  # 弾数があったら撃ち、弾数が減るように

            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if score.value >= 20:
                    score.value -= 20
                    EMP(emys, bombs, screen, exps, score)
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >= 200:
                score.value -= 200
                gravities.add(Gravity(400))
                # ここにあった screen.blit(bg_img, [0, 0]) は削除（ループ先頭へ移動したため）
            if event.type == pg.KEYUP and event.key == pg.K_0:
                if charge_cnt >= 100:
                    for angle in range(-30, 31, 15):
                        beams.add(Beam(bird, angle_offset=angle))
                charge_cnt = 0

        if key_lst[pg.K_0]:
            charge_cnt += 1
        else:
            charge_cnt = 0

        if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        # ボス出現判定: エイリアンを5体倒すと出現
        if enemy_kill_count >= 5 and not any(isinstance(e, Boss) for e in emys):
            emys.add(Boss())
            enemy_kill_count = 0

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        # ボスの移動と攻撃
        for obj in list(emys):
            if isinstance(obj, Boss):
                boss = obj
                if boss.in_burst:
                    boss.shot_frame_count += 1
                    if boss.shot_frame_count >= boss.shot_frame_interval:
                        boss.shot_frame_count = 0
                        if boss.shots_fired < 5:
                            bombs.add(Bomb(boss, bird))
                            boss.shots_fired += 1
                        if boss.shots_fired >= 5:
                            boss.in_burst = False
                            boss.pause_count = boss.pause_frames
                else:
                    boss.pause_count -= 1
                    if boss.pause_count <= 0:
                        boss.in_burst = True
                        boss.shots_fired = 0
                        boss.shot_frame_count = 0

        # ボスへのビーム処理
        collisions = pg.sprite.groupcollide(emys, beams, False, True)
        for emy, hit_beams in collisions.items():
            if isinstance(emy, Boss):
                # ビーム1本につき1ダメージ
                emy.hp -= len(hit_beams) * 1
                if emy.hp <= 0:
                    exps.add(Explosion(emy, 100))
                    score.value += 10
                    bird.change_img(6, screen)
                    emy.kill()
                    bullets.value += 5
            else:
                exps.add(Explosion(emy, 100))  # 爆発エフェクト
                score.value += 10  # 10点アップ
                bird.change_img(6, screen)  # こうかとん喜びエフェクト
                emy.kill()
                enemy_kill_count += 1
                bullets.value += 5

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        # ★追加④ 重力場で敵を破壊
        # 重力場と衝突した敵: 通常は即死だが、ボスは時間経過でダメージ
        grav_coll = pg.sprite.groupcollide(emys, gravities, False, False)
        for emy in grav_coll.keys():
            if isinstance(emy, Boss):
                # ★バグ修正②: 毎フレームだと即死するので10フレームごとに10ダメージに変更
                if tmr % 10 == 0:
                    emy.hp -= 10
                    if emy.hp <= 0:
                        exps.add(Explosion(emy, 100))
                        score.value += 10
                        emy.kill()
                        bullets.value += 5  # 敵を倒したので弾数+5
            else:
                exps.add(Explosion(emy, 100))
                score.value += 10
                emy.kill()
                enemy_kill_count += 1
                bullets.value += 5  # 敵を倒したので弾数+5

        # ★バグ修正③: コメントアウトを解除し重力場で爆弾を消去可能に
        for bomb in pg.sprite.groupcollide(bombs, gravities, True, False).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1
            else:
                life.num -= 1
                if life.num <= 0:
                    bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                    score.update(screen)
                    life.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    return

        # ★追加④: 弾数ゼロでの詰み防止（3秒に1発自動回復、最大5発まで）
        if tmr % 150 == 0 and bullets.value < 5:
            bullets.value += 1

        bird.update(key_lst, screen, score)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        gravities.update()
        gravities.draw(screen)
        exps.update()
        exps.draw(screen)
        score.update(screen)
        bullets.update(screen)  # 弾数の表示
        life.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()