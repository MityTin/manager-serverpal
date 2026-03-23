# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────
#  IV PASSIVE SKILLS DATA  (Source: paldb.cc/en/Iv_Calc)
#  Keyed by passive skill ID.
#  ShotAttack, Defense, CraftSpeed bonuses in % (integer)
# ─────────────────────────────────────────────
IV_PASSIVE_DATA = {
    # ── Tốc độ làm việc ──────────────────────────────────────────────────────
    'CraftSpeed_up3':      {'name': 'Kỹ Năng Siêu Việt (+WS 75%)',        'CraftSpeed': 75},
    'CraftSpeed_up2':      {'name': 'Nghệ Nhân Đích Thực (+WS 50%)',       'CraftSpeed': 50},
    'CraftSpeed_up1':      {'name': 'Chú Tâm (+WS 20%)',                   'CraftSpeed': 20},
    'CraftSpeed_down1':    {'name': 'Vụng Về (-WS 10%)',                   'CraftSpeed': -10},
    'CraftSpeed_down2':    {'name': 'Lười Biếng (-WS 30%)',                'CraftSpeed': -30},
    # ── Phòng thủ ────────────────────────────────────────────────────────────
    'Deffence_up3':        {'name': 'Thân Thể Kim Cương (+Def 30%)',        'Defense': 30},
    'Deffence_up2':        {'name': 'Thân Thể Cường Tráng (+Def 20%)',      'Defense': 20},
    'Deffence_up1':        {'name': 'Da Sắt (+Def 10%)',                    'Defense': 10},
    'Deffence_down1':      {'name': 'Yếu Ớt (-Def 10%)',                   'Defense': -10},
    'Deffence_down2':      {'name': 'Mỏng Manh (-Def 20%)',                'Defense': -20},
    # ── Tấn công / Tổng hợp ──────────────────────────────────────────────────
    'Noukin':              {'name': 'Cơ Bắp (+Atk 30% / -WS 50%)',        'ShotAttack': 30,  'CraftSpeed': -50},
    'Rare':                {'name': 'May Mắn (+Atk 15% / +WS 15%)',        'ShotAttack': 15,  'CraftSpeed': 15},
    'Legend':              {'name': 'Huyền Thoại (+Atk 20% / +Def 20%)',   'ShotAttack': 20,  'Defense': 20},
    'PAL_ALLAttack_up3':   {'name': 'Quỷ Thần (+Atk 30% / +Def 5%)',       'ShotAttack': 30,  'Defense': 5},
    'PAL_ALLAttack_up2':   {'name': 'Cuồng Bạo (+Atk 20%)',                'ShotAttack': 20},
    'PAL_ALLAttack_up1':   {'name': 'Dũng Cảm (+Atk 10%)',                 'ShotAttack': 10},
    'PAL_ALLAttack_down1': {'name': 'Nhút Nhát (-Atk 10%)',                'ShotAttack': -10},
    'PAL_ALLAttack_down2': {'name': 'Dĩ Hòa Vi Quý (-Atk 20%)',           'ShotAttack': -20},
    # ── Hỗn hợp ─────────────────────────────────────────────────────────────
    'PAL_rude':            {'name': 'Thô Lỗ (+Atk 15% / -WS 10%)',         'ShotAttack': 15,  'CraftSpeed': -10},
    'PAL_conceited':       {'name': 'Tự Cao (+WS 10% / -Def 10%)',          'Defense': -10,   'CraftSpeed': 10},
    'PAL_sadist':          {'name': 'Tàn Bạo (+Atk 15% / -Def 15%)',        'ShotAttack': 15,  'Defense': -15},
    'PAL_masochist':       {'name': 'Chịu Trận (-Atk 15% / +Def 15%)',      'ShotAttack': -15, 'Defense': 15},
    'PAL_CorporateSlave':  {'name': 'Đam Mê Công Việc (+WS 30% / -Atk 30%)', 'ShotAttack': -30, 'CraftSpeed': 30},
    'PAL_oraora':          {'name': 'Hung Hăng (+Atk 10% / -Def 10%)',      'ShotAttack': 10,  'Defense': -10},
    # ── Đặc biệt ─────────────────────────────────────────────────────────────
    'CoolTimeReduction_Up_1': {'name': 'Điềm Tĩnh (+Atk 10%)',             'ShotAttack': 10},
    'Alien':               {'name': 'Tế Bào Khác Thường (+Atk 10%)',       'ShotAttack': 10},
    'Nushi':               {'name': 'Thủ Lĩnh (+Def 20%)',                 'Defense': 20},
}
