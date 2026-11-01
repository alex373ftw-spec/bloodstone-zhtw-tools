# -*- coding: utf-8 -*-
"""
007 Blood Stone 汉化文本 简体 -> 繁体 转换器
================================================
.loc 是 OLTX 二进制容器，中文串以 UTF-16LE 存放、以 0x0000 结尾，
与索引数据交错。直接改结构风险高，因此采用：

  1) 以 0x0000 为界切出候选串（两种字节对齐都试）
  2) 用「常用字命中率」区分真实译文与二进制误判
  3) 先找出高置信度译文串（>=0.5），据此划定「文本区块」
  4) 区块内放宽阈值（>=0.30），覆盖「开始」「继续」这类短词
  5) 仅在 UTF-16 编码后字节数完全一致时回写

结果：文件大小、全部偏移与索引保持不变，游戏解析不受影响。
"""
import os, sys, struct

try:
    import opencc
except ImportError:
    print("缺少 opencc：pip install opencc-python-reimplemented")
    sys.exit(1)

CC = opencc.OpenCC('s2twp')

COMMON = set(
    "的一是不了在人有我他这个们中来上大为和国地到以说时要就出会可也你对生能而子那得于着下自之年过发后作里用道行所然家种事成方多经么去法学如都同现当没动面起看定天分还进好小部其些主样理心她本前开但因只从想实日军者意无力它与长把机十民第公此已工使情明性知全三又关点正业外将两高间由问很最重并物手应战向头文体政美相见被利什二等产或新己制身果加西斯月话合回特代内信表化老给世位次度门任常先海通教儿原东声提立及比员解水名真论处走义各入几口认条平系气题活尔更别打女变四神总何电数安少报才结反受目太量再感建务做接必场件计管期市直德资命山金指克许统区保至队形社便空决治展马科司五基眼书非则听白却界达光放强即像难且权思王象完设式色路记南品住告类求据程北边死张该交规万取拉格望觉术领共确传师观清今切院让识候带导争运笑飞风步改收根干造言联持组每济车亲极林服快办议往元英士证近失转夫令准布始怎呢存未远叫台单影具罗字爱击流备兵连调深商算质团集百需价花党华城石级整府离况亚请技际约示复病息究线似官火断精满支视消越器容照须九增研写称企八功吗包片史委乎查轻易早曾除农找装广显吧阿李标谈吃图念六引历首医局突专费号尽另周较注语仅考落青随选列武红响虽推势参希古众构房半节土投某案黑维革划敌致陈律足态护七兴派孩验责营星够章音跟志底站严巴例防族供效续施留讲型料终答紧黄绝奇察母京段依批群项故按河米围江织害斗双境客纪采举杀攻父苏密低朝友诉止细愿千值仍男钱破网热助倒育属坐帝限船脸职速刻乐否刚威毛状率甚独球般普怕弹校苦创假久错承印晚兰试股拿脑预谁益阳若哪微尼继送急血惊伤素药适波夜省初喜卫源食险待述陆习置居劳财环排福纳欢雷警获模充负云停木游龙树疑层冷洲冲射略范竟句室异激汉村哈策演简卡罪判担州静退既衣您宗积余痛检差富灵协角占配征修皮挥胜降阶审沉坚善妈刘读啊超免压银买皇养伊怀执副乱抗犯追帮宣佛岁航优怪香著田铁控税左右份穿艺背阵草脚概恶块顿敢守酒岛托央户烈洋哥索胡款靠评版宝座释景顾弟登货互付伯慢欧换闻危忙核暗姐介坏讨丽良序升监临亮露永呼味野架域沙掉括舰鱼杂误湾吉减编楚肯测败屋跑梦散温困剑渐封救贵枪缺楼县尚毫移娘朋画班智亦耳恩短掌恐遗固席松秘谢鲁遇康虑幸均销钟诗藏赶剧票损忽巨炮旧端探湖录叶春乡附吸予礼港雨呀板庭妇归睛饭额含顺输摇招婚脱补谓督毒油疗旅泽材灭逐莫笔亡鲜词圣择寻厂睡博勒烟授诺伦岸奥唐卖俄炸载洛健堂旁宫喝借君禁阴园谋宋避抓荣姑孙逃牙束跳顶玉镇雪午练迫爷篇肉嘴馆遍凡础洞卷坦牛宁纸诸训私庄祖丝翻暴森塔默握戏隐熟骨访弱蒙歌店鬼软典欲萨伙遭盘爸扩盖弄雄稳忘亿刺拥徒姆杨齐赛趣曲刀床迎冰虚玩析窗醒妻透购替塞努休虎扬途侵刑绿兄迅套贸毕唯谷轮库迹尤竞街促延震弃甲伟麻川申缓潜闪售灯针哲络抵朱埃抱鼓植纯夏忍页杰筑折郑贝尊吴秀混臣雅振染盛怒舞圆搞狂措姓残秋培迷诚宽宇猛摆梅毁伸摩盟末乃悲拍丁赵硬麦蒋操耶阻订彩抽赞魔纷沿喊违妹浪汇币丰蓝殊献桌啦瓦莱援译夺汽烧距裁偏符勇触课敬哭懂墙袭召罚侠厅拜巧侧韩冒债曼融惯享戴童犹乘挂奖绍厚纵障讯涉彻刊丈爆乌役描洗玛患妙镜唱烦签仙彼弗症仿倾牌陷鸟轰咱菜闭奋庆撤泪茶疾缘播朗杜奶季丹狗尾仪偷奔珠虫驻孔宜艾桥淡翼恨繁寒伴叹旦愈潮粮缩罢聚径恰挑袋灰捕徐珍幕映裂泰隔启尖忠累炎暂估泛荒偿横拒瑞忆孤鼻闹羊呆厉衡胞零穷舍码赫婆魂灾洪腿胆津俗辩胸晓劲贫仁偶辑邦恢赖圈摸仰润堆碰艇稍迟辆废净凶署壁御奉旋冬矿抬蛋晨伏吹鸡倍糊秦盾杯租骑乏隆诊奴摄丧污渡旗甘耐凭扎抢绪粗肩梁幻菲皆碎宙叔岩沟贩尤悦"
)

def is_cjk(u):  return 0x4E00 <= u <= 0x9FFF
def is_ext(u):  return 0x3400 <= u <= 0x4DBF
def is_pua(u):  return 0xE000 <= u <= 0xF8FF
def textish(u):
    return (is_cjk(u) or 0x3000 <= u <= 0x303F or 0xFF00 <= u <= 0xFFEF
            or 32 <= u <= 126 or u in (0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2014, 0x2013, 0x00B7, 0x00B0))

def ratio(chars):
    ck = [c for c in chars if is_cjk(ord(c))]
    if not ck:
        return 0.0, 0
    return sum(1 for c in ck if c in COMMON) / len(ck), len(ck)

def runs_of(data):
    """返回 [(start, end, chars_str)]，以 0x0000 或非文本字符为界"""
    n = len(data); out = []
    for al in (0, 1):
        i = al
        while i + 1 < n:
            u = struct.unpack_from('<H', data, i)[0]
            if not textish(u) or u == 0:
                i += 2
                continue
            j = i; chars = []
            while j + 1 < n:
                uu = struct.unpack_from('<H', data, j)[0]
                if uu == 0 or not textish(uu):
                    break
                chars.append(chr(uu)); j += 2
            if len(chars) >= 2:
                out.append((i, j, ''.join(chars)))
            i = j + 2 if j > i else i + 2
    return out

def convert_file(path, out_path):
    data = open(path, 'rb').read()
    n = len(data)
    cand = runs_of(data)

    # 过滤明显垃圾（含扩展区/私用区）
    clean = []
    for s, e, txt in cand:
        if any(is_ext(ord(c)) or is_pua(ord(c)) for c in txt):
            continue
        clean.append((s, e, txt))

    # 高置信度：长串看比例，短串必须全为常用字（避免「啔当」这类二字节垃圾）
    strong = []
    for s, e, txt in clean:
        r, nk = ratio(txt)
        if nk >= 4 and r >= 0.70:
            strong.append((s, e, txt))
        elif nk >= 2 and r >= 1.0:
            strong.append((s, e, txt))

    # 文本区块：高置信度串两侧各扩 700 字节，合并区间
    zones = []
    for s, e, _ in sorted(strong):
        lo, hi = max(0, s - 700), min(n, e + 700)
        if zones and lo <= zones[-1][1]:
            zones[-1][1] = max(zones[-1][1], hi)
        else:
            zones.append([lo, hi])

    def in_zone(pos):
        for lo, hi in zones:
            if lo <= pos < hi:
                return True
        return False

    out = bytearray(data)
    st = {'strong': 0, 'weak': 0, 'changed': 0, 'chars': 0, 'samples': []}

    for s, e, txt in clean:
        r, nk = ratio(txt)
        if nk < 2:
            continue
        at_boundary = (s < 2) or (data[s-2:s] == b'\x00\x00')
        if nk >= 4 and r >= 0.70 and at_boundary:
            ok = True; st['strong'] += 1
        elif nk >= 2 and r >= 1.0 and at_boundary:
            ok = True; st['strong'] += 1
        elif nk >= 2 and r >= 0.60 and in_zone(s) and s >= 2 and data[s-2:s] == b'\x00\x00':
            ok = True; st['weak'] += 1
        else:
            ok = False
        if not ok:
            continue
        t = CC.convert(txt)
        enc = t.encode('utf-16-le')
        if len(enc) != (e - s) or t == txt:
            continue
        out[s:e] = enc
        st['changed'] += 1
        st['chars'] += len(txt)
        if len(st['samples']) < 5:
            st['samples'].append((txt[:34], t[:34]))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, 'wb').write(bytes(out))
    assert len(out) == len(data)
    return st

def main(src_root, dst_root):
    agg = {'files': 0, 'changed': 0, 'chars': 0}
    samples = []
    for dirpath, _, files in os.walk(src_root):
        for fn in sorted(files):
            if not fn.lower().endswith('.loc'):
                continue
            sp = os.path.join(dirpath, fn)
            rel = os.path.relpath(sp, src_root)
            st = convert_file(sp, os.path.join(dst_root, rel))
            agg['files'] += 1
            agg['changed'] += st['changed']
            agg['chars'] += st['chars']
            if st['samples'] and len(samples) < 6:
                samples.append((rel, st['samples'][0]))
    return agg, samples

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    a, s = main(src, dst)
    print(f"处理 {a['files']} 个文件，转换 {a['changed']} 段 / {a['chars']} 字")
    print("\n样例：")
    for rel, (x, y) in s:
        print(f"[{rel}]")
        print(f"  简: {x}")
        print(f"  繁: {y}")
