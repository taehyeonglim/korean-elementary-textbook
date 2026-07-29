#!/usr/bin/env python3
"""Build the complete elementary English worksheet collection.

English pages are text-led and deterministic. GPT Image supplies the two
approved grade-band illustration masters used behind the cover metadata.
"""

from __future__ import annotations

import base64
import argparse
import hashlib
import html
import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
PUBLIC = ROOT / "public"
SVG_ROOT = ROOT / "artifacts" / "worksheet-svg"

UNITS: list[dict[str, Any]] = [
    {
        "id":"english-3-4-alphabet-lab","band":"3-4","domain":"알파벳·소리","module":"Alphabet Lab",
        "standards":["[4영01-01]","[4영01-02]","[4영02-02]"],
        "words":[["A a","apple"],["B b","book"],["C c","cat"],["D d","desk"],["E e","egg"],["F f","fish"]],
        "text":["A is for apple.","B is for book.","C is for cat.","D is for desk.","E is for egg.","F is for fish."],
        "practice":[["A의 소문자를 쓰세요.","a"],["b의 대문자를 쓰세요.","B"],["cat의 첫 글자를 쓰세요.","c"],["fish의 첫 글자를 쓰세요.","f"],["book과 같은 첫소리 단어를 고르세요: desk / ball","ball"]],
        "check":[["Which word begins with C?","cat"],["Which word begins with E?","egg"],["Write the pair for D.","D d"]],
        "produce":["내 이름의 첫 글자를 대문자와 소문자로 쓰기","교실에서 찾은 영어 글자 3개 쓰기"],"model":"T t · P p · B b"
    },
    {
        "id":"english-3-4-sound-and-rhythm","band":"3-4","domain":"소리·읽기","module":"Sound & Rhythm",
        "standards":["[4영01-03]","[4영01-04]","[4영02-01]","[4영02-03]"],
        "words":[["cat","고양이"],["map","지도"],["sun","해"],["run","달리다"],["sit","앉다"],["big","큰"]],
        "text":["Cat, cat, on the map.","Run, run, in the sun.","Sit, sit, by the big cat.","Read each line with a steady beat."],
        "practice":[["c_t의 빈 글자를 쓰세요.","a"],["m_p의 빈 글자를 쓰세요.","a"],["s_n의 빈 글자를 쓰세요.","u"],["r_n의 빈 글자를 쓰세요.","u"],["같은 가운데 소리끼리 짝지으세요: cat / sun / map / run","cat-map, sun-run"]],
        "check":[["Where is the cat?","on the map"],["What do you do in the sun?","run"],["Which words share the short i sound: sit / big / cat?","sit, big"]],
        "produce":["손뼉을 치며 첫 두 문장 읽기","cat, map, sun, run 중 두 단어로 짧은 구 만들기"],"model":"a big cat · run in the sun"
    },
    {
        "id":"english-3-4-classroom-actions","band":"3-4","domain":"교실 영어","module":"Classroom Actions",
        "standards":["[4영01-05]","[4영02-04]","[4영02-06]"],
        "words":[["open","열다"],["close","닫다"],["stand","서다"],["sit","앉다"],["listen","듣다"],["write","쓰다"]],
        "text":["Open your book.","Listen to the teacher.","Write your name.","Close your book.","Stand up and say, “Done!”"],
        "practice":[["책을 펴라는 문장을 쓰세요.","Open your book."],["이름을 쓰라는 문장을 쓰세요.","Write your name."],["앉으라는 표현을 쓰세요.","Sit down."],["close의 반대말을 쓰세요.","open"],["동작 순서의 첫 문장을 쓰세요.","Open your book."]],
        "check":[["What do you write?","your name"],["What do you close?","your book"],["What do you say at the end?","Done!"]],
        "produce":["친구에게 교실 행동 지시 2개 말하기","나만의 3단계 교실 규칙 쓰기"],"model":"Stand up. Open your book. Write one word."
    },
    {
        "id":"english-3-4-me-and-my-people","band":"3-4","domain":"소개·대화","module":"Me & My People",
        "standards":["[4영01-06]","[4영02-05]","[4영02-08]"],
        "words":[["name","이름"],["friend","친구"],["kind","친절한"],["funny","재미있는"],["like","좋아하다"],["together","함께"]],
        "text":["Hi, I’m Mina.","I am ten years old.","This is my friend, Joon.","He is kind and funny.","We like drawing together."],
        "practice":[["Mina의 나이는 몇 살인가요?","ten"],["Joon을 나타내는 낱말 2개를 쓰세요.","kind, funny"],["둘이 함께 좋아하는 일은 무엇인가요?","drawing"],["이름을 묻는 문장을 쓰세요.","What’s your name?"],["좋아하는 것을 묻는 문장을 쓰세요.","What do you like?"]],
        "check":[["Who is Joon?","Mina’s friend"],["Is Joon kind?","Yes, he is."],["What do they like?","They like drawing."]],
        "produce":["짝에게 이름과 좋아하는 것 묻기","나와 친구를 소개하는 3문장 쓰기"],"model":"I’m Yuna. This is Min. We like soccer."
    },
    {
        "id":"english-3-4-feelings-and-kind-talk","band":"3-4","domain":"감정·예절","module":"Feelings & Kind Talk",
        "standards":["[4영02-07]","[4영02-10]"],
        "words":[["happy","기쁜"],["sad","슬픈"],["tired","피곤한"],["sorry","미안한"],["please","부탁할 때"],["thank you","고마울 때"]],
        "text":["A: How are you?","B: I’m tired.","A: Please sit here.","B: Thank you.","A: You’re welcome."],
        "practice":[["기분을 묻는 문장을 쓰세요.","How are you?"],["피곤하다고 답하세요.","I’m tired."],["부탁할 때 덧붙이는 말을 쓰세요.","please"],["도움을 받았을 때 하는 말을 쓰세요.","Thank you."],["Thank you에 알맞게 답하세요.","You’re welcome."]],
        "check":[["How does B feel?","tired"],["What kind word does A use?","please"],["Does the talk end politely?","Yes."]],
        "produce":["happy, sad, tired 중 오늘의 기분 말하기","부탁과 감사가 들어간 4줄 대화 쓰기"],"model":"A: How are you? B: I’m happy. A: Great! B: Thank you."
    },
    {
        "id":"english-3-4-smart-reading","band":"3-4","domain":"읽기 전략·매체","module":"Smart Reading",
        "standards":["[4영01-07]","[4영01-08]","[4영02-09]"],
        "words":[["title","제목"],["picture","그림"],["guess","짐작하다"],["read again","다시 읽다"],["key word","핵심 낱말"],["card","카드"]],
        "text":["Title: A Rainy Day","Look at the cloud picture.","Jin has boots and an umbrella.","He jumps in a puddle.","He feels happy."],
        "practice":[["읽기 전에 먼저 볼 두 가지를 쓰세요.","title, picture"],["Jin이 가진 물건 2개를 쓰세요.","boots, umbrella"],["모르는 문장이 있으면 사용할 전략을 쓰세요.","read again"],["날씨를 나타내는 낱말을 쓰세요.","rainy"],["Jin의 기분을 쓰세요.","happy"]],
        "check":[["What is the title?","A Rainy Day"],["Where does Jin jump?","in a puddle"],["Which clue shows the weather?","cloud / boots / umbrella"]],
        "produce":["제목과 그림 단서로 다음 장면 짐작해 말하기","핵심 낱말 3개로 디지털 카드 문구 만들기"],"model":"Rainy day · red boots · happy jump"
    },
    {
        "id":"english-3-4-story-listening","band":"3-4","domain":"이야기·공감","module":"A Small Seed",
        "standards":["[4영01-09]"],
        "words":[["seed","씨앗"],["soil","흙"],["rain","비"],["sun","해"],["grow","자라다"],["flower","꽃"]],
        "text":["A small seed sleeps in the soil.","Rain comes. The seed wakes up.","The sun shines. A green stem grows.","At last, a yellow flower smiles."],
        "practice":[["씨앗이 처음 있는 곳은 어디인가요?","in the soil"],["씨앗을 깨우는 것은 무엇인가요?","rain"],["비 다음에 오는 것은 무엇인가요?","the sun"],["마지막에 피는 것은 무엇인가요?","a yellow flower"],["이야기의 기분을 한 낱말로 쓰세요.","happy / hopeful"]],
        "check":[["What color is the stem?","green"],["What color is the flower?","yellow"],["Put in order: flower / seed / stem","seed, stem, flower"]],
        "produce":["가장 마음에 드는 장면과 까닭 말하기","씨앗에게 한 문장 편지 쓰기"],"model":"Dear Seed, grow strong and bright!"
    },
    {
        "id":"english-3-4-culture-around-us","band":"3-4","domain":"문화·존중","module":"Hello Around Us",
        "standards":["[4영01-10]"],
        "words":[["hello","안녕하세요"],["bow","인사로 고개 숙이기"],["wave","손 흔들기"],["share","나누다"],["different","다른"],["respect","존중하다"]],
        "text":["People greet in different ways.","Some people wave. Some people bow.","Families eat different foods.","Different can be interesting.","We listen, learn, and show respect."],
        "practice":[["사람들이 하는 인사 2가지를 쓰세요.","wave, bow"],["가족마다 다를 수 있는 것을 쓰세요.","foods"],["different의 뜻을 쓰세요.","다른"],["존중하는 행동 2개를 찾으세요.","listen, learn"],["글의 중심 낱말을 쓰세요.","respect"]],
        "check":[["Do all people greet in one way?","No."],["Can different be interesting?","Yes."],["How do we show respect?","We listen and learn."]],
        "produce":["내가 아는 인사 방법 하나 소개하기","다른 생활 방식을 존중하는 약속 쓰기"],"model":"We can listen. We can ask kindly. We respect differences."
    },
    {
        "id":"english-5-6-speak-with-rhythm","band":"5-6","domain":"소리·유창성","module":"Speak with Rhythm",
        "standards":["[6영01-01]","[6영01-02]","[6영02-01]"],
        "words":[["question","질문"],["answer","대답"],["stress","강세"],["rhythm","리듬"],["rise","올라가다"],["fall","내려가다"]],
        "text":["Do you like music? ↗","Yes, I do. ↘","What do you play? ↘","I play the drums. ↘","Read in thought groups: I play / after school."],
        "practice":[["Yes/No 질문 끝에 알맞은 기호를 쓰세요.","↗"],["평서문 끝에 알맞은 기호를 쓰세요.","↘"],["I play the drums.에서 강하게 읽을 핵심어를 쓰세요.","play, drums"],["의미 단위로 나누세요: I practice after school.","I practice / after school."],["질문에 답하세요: Do you like music?","Yes, I do. / No, I don’t."]],
        "check":[["Which sentence is a yes/no question?","Do you like music?"],["What does the speaker play?","the drums"],["When does the speaker play?","after school"]],
        "produce":["올라가는 억양과 내려가는 억양으로 대화 읽기","취미에 관한 질문과 대답 2쌍 쓰기"],"model":"Do you like art? Yes, I do. What do you draw? I draw animals."
    },
    {
        "id":"english-5-6-detail-detective","band":"5-6","domain":"세부 정보·질문","module":"Detail Detective",
        "standards":["[6영01-03]","[6영01-04]","[6영02-07]"],
        "words":[["when","언제"],["where","어디"],["who","누구"],["bring","가져오다"],["meet","만나다"],["library","도서관"]],
        "text":["Book Club Notice","When: Friday, 3:30 p.m.","Where: School library","Bring: one favorite book","Meet Ms. Han by the front desk."],
        "practice":[["모임 요일을 쓰세요.","Friday"],["모임 시각을 쓰세요.","3:30 p.m."],["장소를 쓰세요.","school library"],["가져갈 것을 쓰세요.","one favorite book"],["만날 사람을 쓰세요.","Ms. Han"]],
        "check":[["When is the club?","Friday at 3:30 p.m."],["Where do students meet Ms. Han?","by the front desk"],["What question asks for a place?","Where is the club?"]],
        "produce":["공지의 세부 정보를 묻는 질문 3개 말하기","나만의 짧은 모임 공지 쓰기"],"model":"Art Club · Tuesday, 2:30 p.m. · Art room · Bring a pencil."
    },
    {
        "id":"english-5-6-find-the-main-idea","band":"5-6","domain":"중심 내용·전략","module":"Find the Main Idea",
        "standards":["[6영01-05]","[6영01-07]"],
        "words":[["main idea","중심 생각"],["detail","세부 내용"],["title","제목"],["predict","예측하다"],["scan","찾아 읽다"],["check","확인하다"]],
        "text":["Our Class Garden","Our class grows vegetables behind the school.","Each team waters the plants on a different day.","We use the vegetables in a class salad.","The garden helps us learn and work together."],
        "practice":[["글의 제목을 쓰세요.","Our Class Garden"],["학생들이 기르는 것을 쓰세요.","vegetables"],["학생들이 식물에 하는 일을 쓰세요.","water the plants"],["채소로 만드는 것을 쓰세요.","a class salad"],["가장 알맞은 중심 생각을 쓰세요.","The class learns and works together through a garden."]],
        "check":[["Where is the garden?","behind the school"],["Does every team water on the same day?","No."],["Which strategy finds one fact quickly?","scan"]],
        "produce":["제목을 보고 읽기 전 예측 말하기","중심 생각 1문장과 뒷받침 내용 2개 쓰기"],"model":"Main idea: Our garden brings the class together. Details: Teams water plants. We make salad."
    },
    {
        "id":"english-5-6-sequence-and-howto","band":"5-6","domain":"순서·방법","module":"Sequence & How-to",
        "standards":["[6영01-06]","[6영02-05]"],
        "words":[["first","먼저"],["next","다음에"],["then","그런 다음"],["finally","마지막으로"],["pour","붓다"],["mix","섞다"]],
        "text":["How to Make Lemon Water","First, wash one lemon.","Next, cut the lemon with an adult.","Then, put the slices in water.","Finally, mix and enjoy."],
        "practice":[["가장 먼저 하는 일을 쓰세요.","wash one lemon"],["레몬을 자를 때 함께해야 하는 사람은 누구인가요?","an adult"],["물에 넣는 것을 쓰세요.","the slices"],["mix 앞의 순서 낱말을 쓰세요.","finally"],["순서 낱말 4개를 차례로 쓰세요.","first, next, then, finally"]],
        "check":[["What comes after washing?","cut the lemon"],["What comes before mixing?","put the slices in water"],["Is this a story or a how-to text?","a how-to text"]],
        "produce":["손 씻는 방법을 순서대로 말하기","4단계 방법 설명문 쓰기"],"model":"First, turn on the water. Next, use soap. Then, wash well. Finally, dry your hands."
    },
    {
        "id":"english-5-6-describe-clearly","band":"5-6","domain":"묘사·문장","module":"Describe Clearly",
        "standards":["[6영02-02]","[6영02-03]","[6영02-04]"],
        "words":[["curly","곱슬곱슬한"],["quiet","조용한"],["bright","밝은"],["round","둥근"],["useful","유용한"],["because","왜냐하면"]],
        "text":["This is my friend, Sora.","She has curly hair and a bright smile.","She is quiet, but she is very helpful.","Her blue bag is big and useful.","I like Sora because she is kind."],
        "practice":[["Sora의 머리 모양을 쓰세요.","curly"],["Sora의 미소를 나타내는 낱말을 쓰세요.","bright"],["가방의 색을 쓰세요.","blue"],["문장을 바르게 고치세요: she is kind","She is kind."],["물음표가 필요한 문장을 고르세요: She is kind / Is she kind","Is she kind?"]],
        "check":[["What is Sora like?","quiet, helpful, kind"],["What is big and useful?","her blue bag"],["Why does the writer like Sora?","because she is kind"]],
        "produce":["친구나 물건의 특징을 3문장으로 말하기","대문자와 문장 부호를 확인해 묘사 글 쓰기"],"model":"This is my pencil case. It is round and bright. I like it because it is useful."
    },
    {
        "id":"english-5-6-feelings-plans","band":"5-6","domain":"감정·경험·계획","module":"Feelings, Experiences & Plans",
        "standards":["[6영02-06]"],
        "words":[["excited","신이 난"],["proud","자랑스러운"],["because","왜냐하면"],["yesterday","어제"],["tomorrow","내일"],["plan","계획"]],
        "text":["Yesterday, I finished my first long book.","I felt proud because I did not give up.","Tomorrow, I will visit the library.","I plan to choose a mystery story.","I am excited about my next book."],
        "practice":[["글쓴이가 어제 끝낸 것을 쓰세요.","a long book"],["글쓴이의 기분을 쓰세요.","proud"],["그렇게 느낀 까닭을 쓰세요.","because the writer did not give up"],["내일 갈 장소를 쓰세요.","the library"],["고를 책의 종류를 쓰세요.","a mystery story"]],
        "check":[["What happened yesterday?","The writer finished a long book."],["What is the plan for tomorrow?","Visit the library and choose a mystery story."],["How does the writer feel now?","excited"]],
        "produce":["최근 경험과 기분을 because로 연결해 말하기","어제의 경험 1문장과 내일의 계획 2문장 쓰기"],"model":"Yesterday, I played in a concert. I felt happy because my friends came. Tomorrow, I will rest."
    },
    {
        "id":"english-5-6-write-for-a-purpose","band":"5-6","domain":"목적 글쓰기·매체","module":"Write for a Purpose",
        "standards":["[6영02-08]","[6영02-09]"],
        "words":[["to","받는 사람"],["from","보낸 사람"],["invite","초대하다"],["thank","감사하다"],["date","날짜"],["place","장소"]],
        "text":["To: Alex","Please come to our class game day!","Date: May 20, 2 p.m.","Place: School gym","From: Class 6"],
        "practice":[["받는 사람을 쓰세요.","Alex"],["글의 목적을 쓰세요.","to invite Alex"],["날짜와 시각을 쓰세요.","May 20, 2 p.m."],["장소를 쓰세요.","school gym"],["보낸 사람을 쓰세요.","Class 6"]],
        "check":[["What kind of message is this?","an invitation"],["What information helps Alex arrive?","date, time, place"],["Which line is the greeting/request?","Please come to our class game day!"]],
        "produce":["목적에 맞는 매체를 하나 고르고 까닭 말하기","예시를 참고해 초대 또는 감사 카드 쓰기"],"model":"To: Mina · Thank you for your help. You made our project better! · From: Joon"
    },
    {
        "id":"english-5-6-stories-culture-team","band":"5-6","domain":"이야기·문화·협력","module":"Stories Connect Us",
        "standards":["[6영01-08]","[6영01-09]","[6영01-10]","[6영02-10]"],
        "words":[["story","이야기"],["view","관점"],["custom","생활 문화"],["compare","비교하다"],["agree","동의하다"],["add","덧붙이다"]],
        "text":["Four students read a story about sharing food.","Lina says, “The family eats together on a mat.”","Joon says, “My family eats together at a table.”","They find a difference and the same warm feeling.","The team listens and makes one culture poster together."],
        "practice":[["학생들이 읽은 이야기의 주제를 쓰세요.","sharing food"],["Lina의 가족이 식사하는 곳을 쓰세요.","on a mat"],["Joon의 가족이 식사하는 곳을 쓰세요.","at a table"],["두 가족에게 같은 것을 쓰세요.","a warm feeling / eating together"],["모둠이 함께 만든 것을 쓰세요.","a culture poster"]],
        "check":[["Do the students have the same custom?","No."],["What do they do before making the poster?","They listen."],["What attitude does the text show?","openness and respect"]],
        "produce":["I agree / I want to add로 모둠 의견 이어 말하기","두 문화를 비교하고 공통점을 존중하는 4문장 쓰기"],"model":"The places are different. Both families eat together. I like both ideas. We can learn from each other."
    },
]

W, H, M = 1024, 1536, 72
COLORS = {"paper":"#FFFDF8","ink":"#172A46","muted":"#53657A","blue":"#285A9F","sky":"#DCEEFF","coral":"#F47C68","mint":"#DDF4EC","line":"#C8D8E8","yellow":"#FFF1BA"}
FONT = "Apple SD Gothic Neo, Noto Sans KR, sans-serif"

def esc(value: Any) -> str: return html.escape(str(value), quote=True)
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def text(value: str, x: float, y: float, size: int, color: str = COLORS["ink"], weight: int = 500, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(value)}</text>'

def wrap(value: str, limit: int) -> list[str]:
    words, lines, current = value.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) > limit and current:
            lines.append(current); current = word
        else: current = trial
    if current: lines.append(current)
    return lines

def para(value: str, x: int, y: int, size: int, limit: int, line_height: int, color: str = COLORS["ink"], weight: int = 500) -> str:
    lines = wrap(value, limit)
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else line_height}">{esc(line)}</tspan>' for i, line in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{spans}</text>'

def shell(unit: dict[str, Any], page: int, label: str) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{COLORS["paper"]}"/>',
        f'<rect width="{W}" height="184" fill="{COLORS["blue"]}"/>',
        text("초등 영어 한 장", M, 54, 21, "#FFFFFF", 700),
        text(unit["module"], M, 108, 40, "#FFFFFF", 800),
        text(f'{unit["band"]}학년군 · {unit["domain"]} · {label}', M, 151, 20, "#FFFFFF", 600),
        text(str(page), W-M, 151, 21, "#FFFFFF", 700, "end"),
    ]

def footer(parts: list[str]) -> None:
    parts += [f'<line x1="{M}" y1="1460" x2="{W-M}" y2="1460" stroke="{COLORS["line"]}" stroke-width="2"/>',
              text("Taehyeong Lim · CC BY-NC-SA 4.0", M, 1495, 15, COLORS["muted"], 600),
              text("표지 이미지: GPT Image · Gongnyang Prompt Kit", W-M, 1495, 15, COLORS["muted"], 500, "end"),
              "</svg>"]

def cover(unit: dict[str, Any]) -> str:
    master = ROOT / "assets" / "cover-masters" / f'english-{unit["band"]}.png'
    data = base64.b64encode(master.read_bytes()).decode()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {W} {H}">',
             f'<image href="data:image/png;base64,{data}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>',
             '<rect x="54" y="54" width="916" height="174" rx="24" fill="#FFFDF8" opacity=".94"/>',
             text("초등 영어 한 장", 86, 112, 28, COLORS["blue"], 800),
             text(f'{unit["band"]}학년군 · {unit["domain"]}', 86, 158, 19, COLORS["muted"], 700),
             para(" ".join(unit["standards"]), 86, 198, 16, 64, 22, COLORS["muted"], 650),
             '<rect x="54" y="1130" width="916" height="332" rx="24" fill="#FFFDF8" opacity=".96"/>',
             text(unit["module"], 86, 1215, 48, COLORS["blue"], 800),
             text("READ · PRACTICE · SPEAK · WRITE", 86, 1265, 18, COLORS["coral"], 800),
             text("Taehyeong Lim · CC BY-NC-SA 4.0", 86, 1378, 16, COLORS["blue"], 700),
             text("이미지 제작: GPT Image · Gongnyang Prompt Kit", 86, 1415, 16, COLORS["blue"], 700),
             "</svg>"]
    return "\n".join(parts)

def input_page(unit: dict[str, Any]) -> str:
    p = shell(unit, 2, "읽고 익히기")
    p += [text("WORD BANK", M, 236, 18, COLORS["coral"], 800), text("먼저 낱말을 읽고 뜻을 확인하세요.", M, 274, 24, weight=700)]
    for i, (word, meaning) in enumerate(unit["words"]):
        col, row = i % 2, i // 2; x, y = M + col*454, 314 + row*90
        p += [f'<rect x="{x}" y="{y}" width="426" height="68" rx="16" fill="{COLORS["sky"]}"/>', text(word, x+20, y+30, 22, COLORS["blue"], 800), text(meaning, x+20, y+55, 16, COLORS["muted"], 600)]
    p += [text("READING", M, 640, 18, COLORS["coral"], 800), f'<rect x="{M}" y="674" width="{W-2*M}" height="548" rx="24" fill="#FFFFFF" stroke="{COLORS["line"]}" stroke-width="2"/>']
    for i, line in enumerate(unit["text"]): p.append(para(line, M+34, 738+i*82, 27, 47, 34, COLORS["ink"], 650))
    p += [f'<rect x="{M}" y="1252" width="{W-2*M}" height="138" rx="20" fill="{COLORS["mint"]}"/>', text("읽기 전략", M+28, 1294, 18, COLORS["blue"], 800), para("제목과 낱말 단서를 먼저 보고, 문장을 소리 내어 두 번 읽으세요.", M+28, 1334, 22, 50, 30, COLORS["ink"], 600)]
    footer(p); return "\n".join(p)

def list_page(unit: dict[str, Any], page: int, label: str, title_value: str, items: list[list[str]], answer_mode: bool = False) -> str:
    p = shell(unit, page, label)
    p += [text(title_value, M, 244, 30, COLORS["blue"], 800)]
    for i, item in enumerate(items):
        y = 292+i*205
        p += [f'<rect x="{M}" y="{y}" width="{W-2*M}" height="178" rx="22" fill="#FFFFFF" stroke="{COLORS["line"]}" stroke-width="2"/>',
              f'<circle cx="{M+28}" cy="{y+39}" r="24" fill="{COLORS["coral"]}"/>',
              text(str(i+1), M+28, y+48, 25, "#FFFFFF", 800, "middle"),
              para(item[0], M+70, y+48, 23, 54, 31, COLORS["ink"], 650)]
        if answer_mode:
            p.append(para(item[1], M+70, y+125, 22, 52, 29, COLORS["blue"], 800))
        else:
            p += [f'<line x1="{M+70}" y1="{y+126}" x2="{W-M-34}" y2="{y+126}" stroke="{COLORS["line"]}" stroke-width="2"/>',
                  f'<line x1="{M+70}" y1="{y+158}" x2="{W-M-34}" y2="{y+158}" stroke="{COLORS["line"]}" stroke-width="2"/>']
    footer(p); return "\n".join(p)

def production_page(unit: dict[str, Any]) -> str:
    p = shell(unit, 5, "말하고 쓰기")
    p += [text("USE ENGLISH", M, 242, 18, COLORS["coral"], 800), text("읽은 표현을 나의 말과 글로 바꾸어 보세요.", M, 282, 28, COLORS["blue"], 800)]
    for i, prompt in enumerate(unit["produce"]):
        y = 340+i*340
        p += [f'<rect x="{M}" y="{y}" width="{W-2*M}" height="300" rx="24" fill="{"#FFFFFF" if i else COLORS["mint"]}" stroke="{COLORS["line"]}" stroke-width="2"/>',
              text(f'{i+1}. {"SPEAK" if i == 0 else "WRITE"}', M+28, y+48, 18, COLORS["coral"], 800),
              para(prompt, M+28, y+92, 25, 52, 34, COLORS["ink"], 700)]
        for line in range(4): p.append(f'<line x1="{M+30}" y1="{y+160+line*34}" x2="{W-M-30}" y2="{y+160+line*34}" stroke="{COLORS["line"]}" stroke-width="2"/>')
    p += [f'<rect x="{M}" y="1050" width="{W-2*M}" height="292" rx="24" fill="{COLORS["yellow"]}"/>', text("MODEL", M+28, 1102, 18, COLORS["blue"], 800), para(unit["model"], M+28, 1152, 25, 48, 35, COLORS["ink"], 700), text("모델을 그대로 베끼기보다 낱말과 내용을 바꾸어 표현하세요.", M+28, 1300, 17, COLORS["muted"], 600)]
    footer(p); return "\n".join(p)

def answer_page(unit: dict[str, Any]) -> str:
    p = shell(unit, 6, "정답·예시 답안")
    p += [text("PRACTICE", M, 238, 18, COLORS["coral"], 800)]
    for i, (_, answer) in enumerate(unit["practice"]):
        y = 278+i*92
        p += [text(f"{i+1}.", M, y, 21, COLORS["blue"], 800), para(answer, M+48, y, 20, 66, 27, COLORS["ink"], 650)]
    p += [text("CHECK THE TEXT", M, 780, 18, COLORS["coral"], 800)]
    for i, (_, answer) in enumerate(unit["check"]):
        y = 824+i*100
        p += [text(f"{i+1}.", M, y, 21, COLORS["blue"], 800), para(answer, M+48, y, 20, 66, 27, COLORS["ink"], 650)]
    p += [f'<rect x="{M}" y="1135" width="{W-2*M}" height="225" rx="22" fill="{COLORS["yellow"]}"/>', text("말하기·쓰기 예시", M+28, 1182, 18, COLORS["blue"], 800), para(unit["model"], M+28, 1230, 22, 55, 31, COLORS["ink"], 700), text("자유 응답은 의미가 통하고 활동 조건에 맞으면 정답으로 봅니다.", M+28, 1328, 16, COLORS["muted"], 600)]
    footer(p); return "\n".join(p)

def rasterize(source: Path, webp: Path) -> None:
    png = webp.with_suffix(".png")
    subprocess.run(["node", str(ROOT/"scripts/rasterize-svg.mjs"), str(source), str(png), str(webp)], cwd=ROOT, check=True)
    png.unlink()

def build_pdf(workbook: dict[str, Any]) -> None:
    target = PUBLIC / workbook["pdf"]["path"].lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = canvas.Canvas(str(target), pagesize=A4, pageCompression=1)
    doc.setTitle(workbook["title"]); doc.setAuthor(workbook["author"])
    doc.setSubject(" · ".join(workbook["standardCodes"])); doc.setCreator("초등 영어 한 장 deterministic worksheet renderer")
    pw, ph = A4
    for page in workbook["pages"]:
        image = Image.open(PUBLIC/page["imagePath"].lstrip("/"))
        doc.drawImage(ImageReader(image), 0, 0, pw, ph, mask="auto"); doc.showPage()
    doc.save()

def transcript(unit: dict[str, Any], workbook: dict[str, Any]) -> str:
    words = "".join(f"<li><strong>{esc(w)}</strong>: {esc(m)}</li>" for w,m in unit["words"])
    reading = "".join(f"<p lang='en'>{esc(line)}</p>" for line in unit["text"])
    practice = "".join(f"<li>{esc(q)} <strong>정답: {esc(a)}</strong></li>" for q,a in unit["practice"])
    checks = "".join(f"<li>{esc(q)} <strong>정답: {esc(a)}</strong></li>" for q,a in unit["check"])
    return f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{esc(workbook['title'])} 전문</title></head><body><main><h1>{esc(workbook['title'])}</h1><p>{' '.join(workbook['standardCodes'])}</p><h2>낱말</h2><ul>{words}</ul><h2>읽기</h2>{reading}<h2>연습과 정답</h2><ol>{practice}</ol><h2>내용 확인과 정답</h2><ol>{checks}</ol><h2>말하고 쓰기</h2><ul><li>{esc(unit['produce'][0])}</li><li>{esc(unit['produce'][1])}</li></ul><p><strong>예시:</strong> {esc(unit['model'])}</p></main></body></html>\n"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", action="append", help="Render only this English workbook ID; repeatable.")
    args = parser.parse_args()
    selected = set(args.unit or [])
    units = [unit for unit in UNITS if not selected or unit["id"] in selected]
    missing = selected - {unit["id"] for unit in units}
    if missing: raise ValueError(f"Unknown English workbook IDs: {', '.join(sorted(missing))}")
    catalog_path = CONTENT/"catalog.json"; catalog = json.loads(catalog_path.read_text())
    replace_ids = {unit["id"] for unit in units}
    catalog["workbooks"] = [w for w in catalog["workbooks"] if w["id"] not in replace_ids]
    for unit in units:
        slug = unit["id"]; out = PUBLIC/"workbooks"/slug; svg_dir = SVG_ROOT/slug
        out.mkdir(parents=True, exist_ok=True); svg_dir.mkdir(parents=True, exist_ok=True)
        sources = [cover(unit), input_page(unit), list_page(unit,3,"표현 연습","PRACTICE",unit["practice"]), list_page(unit,4,"내용 확인","CHECK THE TEXT",unit["check"]), production_page(unit), answer_page(unit)]
        page_names = ["01-cover","02-input","03-practice","04-check","05-speak-write","06-answers"]
        roles = ["cover","worksheet","worksheet","worksheet","worksheet","answer"]
        pages = []
        for i, (name, source, role) in enumerate(zip(page_names,sources,roles),1):
            svg = svg_dir/f"{name}.svg"; webp = out/f"{name}.webp"
            svg.write_text(source, encoding="utf-8"); rasterize(svg,webp)
            pages.append({"id":name[3:],"order":i,"role":role,"imagePath":f"/workbooks/{slug}/{name}.webp","thumbnailPath":f"/workbooks/{slug}/{name}.webp","sha256":sha(webp),"alt":f'{unit["module"]} {i}쪽',"approved":True})
        workbook = {"id":slug,"slug":slug,"subject":"english","title":f'초등 영어 한 장: {unit["module"]}',"gradeBand":unit["band"],"domain":unit["domain"],"module":unit["module"],"standardCodes":unit["standards"],"levels":["input","practice","production"],"activities":{"words":unit["words"],"text":unit["text"],"practice":unit["practice"],"check":unit["check"],"produce":unit["produce"],"model":unit["model"]},"pages":pages,"pdf":{"path":f"/workbooks/{slug}/{slug}.pdf","pageCount":6,"sha256":"0"*64},"transcriptPath":f"/workbooks/{slug}/transcript.html","license":"CC-BY-NC-SA-4.0","author":"Taehyeong Lim","publishedAt":"2026-07-29","published":True}
        build_pdf(workbook); workbook["pdf"]["sha256"] = sha(PUBLIC/workbook["pdf"]["path"].lstrip("/"))
        (out/"transcript.html").write_text(transcript(unit,workbook),encoding="utf-8")
        (CONTENT/"workbooks"/f"{slug}.json").write_text(json.dumps(workbook,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        catalog["workbooks"].append(workbook)
        print(f"Rendered {slug}: 6 pages")
    catalog["workbooks"].sort(key=lambda item:item["id"])
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__ == "__main__": raise SystemExit(main())
