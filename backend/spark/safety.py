import re
import unicodedata

# Conservative MVP gate. Unknown personal introductions are rejected rather than
# forwarded. This is defense in depth, not a complete child-safety classifier.
PRIVATE = re.compile(r'我叫|姓名|学校|小学[一二三四五六]?年级[一二三四五六七八九十0-9]+班|住在|地址|电话|手机号|微信|身份证|邮箱|my name|my school|my address|\b1[3-9]\d{9}\b|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b\d{15,18}[Xx]?\b', re.I)
DANGER = re.compile(r'自杀|不想活|伤害自己|想死|被打|虐待|kill myself|suicide|self.harm', re.I)
UNSAFE = re.compile(r'色情|裸体|做爱|性视频|制造炸弹|制作炸弹|毒品制作|杀人方法|porn|make a bomb|kill someone', re.I)
INJECTION = re.compile(r'忽略.{0,12}(指令|规则)|系统提示|ignore.{0,20}instructions|system prompt|api.?key|app.?secret', re.I)

def normalize(text: str) -> str:
    return unicodedata.normalize('NFKC', text).strip()

def safety_reply(text: str) -> str | None:
    text = normalize(text)
    if DANGER.search(text):
        return '谢谢你告诉我。你的安全很重要。请现在联系身边可信任的家长、老师或其他成年人，和他们待在一起。如果你正处在危险中，请让他们帮助联系当地紧急救援。我是 AI，不能替代现实中的帮助。'
    if PRIVATE.search(text):
        return '保护好自己的隐私哦。请不要告诉我真实姓名、学校、地址或联系方式，只发送想学习的问题就可以。'
    if UNSAFE.search(text) or INJECTION.search(text):
        return '这个内容不适合在这里展开。我们可以一起探索安全的数学或科学问题；涉及身体或安全的问题，也可以请家长或老师帮助。'
    return None

def safe_source(text: str) -> bool:
    return not (PRIVATE.search(text) or UNSAFE.search(text) or INJECTION.search(text))
