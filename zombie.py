from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import common

# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')

    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0  # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0

        self.tx, self.ty = 1000, 1000
        self.build_behavior_tree()

    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50

    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        self.bt.run()

    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        #Zombie.marker_image.draw(self.tx + 25, self.ty - 25)
        draw_rectangle(*self.get_bb())
        draw_circle(self.x, self.y, int(PIXEL_PER_METER * 7), 255, 255, 0)

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1

    def set_target_location(self, x=None, y=None):
        if x is None and y is None:
            raise ValueError('목적지 좌표가 없습니다.')
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (PIXEL_PER_METER * r) ** 2

    def move_little_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = game_framework.frame_time * RUN_SPEED_PPS
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_little_to(self.tx, self.ty)
        if self.distance_less_than(self.tx, self.ty, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.RUNNING

    def set_random_location(self):
        self.tx, self.ty = random.randint(100, 1280 - 100), random.randint(100, 1024 - 100)
        return BehaviorTree.SUCCESS

    def is_boy_nearby(self, r):
        if self.distance_less_than(common.boy.x, common.boy.y, self.x, self.y, r):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def has_more_balls(self):
        if self.ball_count >= common.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def chase_boy(self):
        self.state = 'Walk'
        self.tx, self.ty = common.boy.x, common.boy.y
        self.move_little_to(self.tx, self.ty)
        return BehaviorTree.RUNNING

    def flee_from_boy(self):
        self.state = 'Walk'
        dx = self.x - common.boy.x
        dy = self.y - common.boy.y
        self.dir = math.atan2(dy, dx)

        distance = game_framework.frame_time * RUN_SPEED_PPS
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)


        return BehaviorTree.RUNNING

    def build_behavior_tree(self):
        a1 = Action('랜덤 위치 설정', self.set_random_location)
        a2 = Action('목적지로 이동', self.move_to)
        wander = Sequence('배회', a1, a2)


        c1 = Condition('소년이 근처에 있는가?', self.is_boy_nearby, 7)
        c2 = Condition('공이 더 많은가?', self.has_more_balls)

        a_chase = Action('소년 추적', self.chase_boy)
        a_flee = Action('소년에게서 도망', self.flee_from_boy)

        chase_seq = Sequence('추적', c2, a_chase)
        chase_or_flee_sel = Selector('추적 또는 도망', chase_seq, a_flee)
        interact_with_boy = Sequence('소년 상호작용', c1, chase_or_flee_sel)
        root = Selector('행동', interact_with_boy, wander)

        self.bt = BehaviorTree(root)