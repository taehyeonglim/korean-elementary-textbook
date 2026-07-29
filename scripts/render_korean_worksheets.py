#!/usr/bin/env python3
"""Render 18 Korean-language workbooks covering all 87 curriculum standards."""

from __future__ import annotations

import argparse
import base64
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
CONTENT, PUBLIC = ROOT/"content", ROOT/"public"
SVG_ROOT = ROOT/"artifacts"/"worksheet-svg"

def codes(grade: int, domain: int, count: int) -> list[str]:
    return [f"[{grade}국{domain:02d}-{index:02d}]" for index in range(1, count+1)]

UNITS: list[dict[str, Any]] = [
 {"id":"korean-1-2-listening-speaking","band":"1-2","domain":"듣기·말하기","module":"차례를 지키며 마음 나누기","standards":codes(2,1,5),
  "a":["비 오는 아침","아침에 비가 내렸습니다.","서윤이는 우산을 챙겨 학교에 갔습니다.","교실 앞에서 젖은 친구를 보고 수건을 건넸습니다.","친구는 고맙다고 말했고 두 사람은 함께 웃었습니다."],
  "qa":[["언제 비가 내렸나요?","아침"],["서윤이가 챙긴 것은 무엇인가요?","우산"],["서윤이는 친구에게 무엇을 건넸나요?","수건"],["일어난 일을 차례대로 쓰세요.","비가 옴 → 우산을 챙김 → 수건을 건넴 → 함께 웃음"]],
  "b":["마음을 나누는 대화","민준: 내 색연필이 부러져서 속상해.","하린: 많이 아끼던 색연필이었구나.","민준: 응. 내 말을 들어줘서 고마워.","하린: 함께 새 색연필을 찾아보자."],
  "qb":[["민준이의 감정은 무엇인가요?","속상함"],["하린은 민준의 말을 어떻게 들었나요?","감정을 헤아리며 집중해서 들었다."],["바르고 고운 말을 한 곳을 찾으세요.","내 말을 들어줘서 고마워."],["두 사람이 대화할 때 지켜야 할 것은 무엇인가요?","말차례"]],
  "focus":[["발표할 때 몸은 어떻게 하나요?","바르게 선다."],["친구가 말할 때 무엇을 하나요?","집중해서 듣는다."],["내 차례가 아니면 어떻게 하나요?","기다린다."],["경험 발표의 순서를 쓰세요.","언제·어디서 → 한 일 → 생각이나 느낌"]],
  "produce":["최근에 친구와 마음을 나눈 경험을 세 문장으로 말해 보세요.","짝과 번갈아 질문하고 대답한 뒤, 잘 들었다는 표시를 해 보세요."],"model":"어제 운동장에서 친구가 넘어졌습니다. 나는 친구의 말을 듣고 보건실에 함께 갔습니다. 친구가 안심해서 나도 기뻤습니다."},
 {"id":"korean-1-2-reading","band":"1-2","domain":"읽기","module":"또박또박 읽고 마음 짐작하기","standards":codes(2,2,5),
  "a":["화분의 새싹","지우는 작은 화분에 씨앗을 심었습니다.","매일 물을 주었지만 며칠 동안 아무 변화가 없었습니다.","어느 아침, 흙 사이로 연두색 새싹이 고개를 내밀었습니다.","지우는 두 손을 모으고 한참 새싹을 바라보았습니다."],
  "qa":[["지우가 심은 것은 무엇인가요?","씨앗"],["며칠 동안 변화가 있었나요?","없었다."],["어느 아침 무엇이 나왔나요?","연두색 새싹"],["지우의 마음을 짐작하고 근거를 쓰세요.","기쁘고 신기하다. 두 손을 모으고 한참 바라보았기 때문이다."]],
  "b":["도서관 가는 날","우리 반은 금요일마다 도서관에 갑니다.","친구들은 읽고 싶은 책을 스스로 고릅니다.","책을 다 읽으면 기억에 남는 장면을 한 문장으로 적습니다.","우리는 서로의 문장을 읽으며 다음 책을 찾습니다."],
  "qb":[["언제 도서관에 가나요?","금요일마다"],["책은 누가 고르나요?","친구들이 스스로"],["읽은 뒤 무엇을 적나요?","기억에 남는 장면"],["글의 중심 내용을 쓰세요.","우리 반은 도서관에서 즐겁게 책을 읽고 나눈다."]],
  "focus":[["의미가 잘 드러나게 읽으려면 무엇을 살피나요?","문장의 뜻과 알맞은 띄어 읽기"],["쉼표에서는 어떻게 읽나요?","조금 쉰다."],["마침표에서는 어떻게 읽나요?","문장을 마치며 쉰다."],["읽고 싶은 책을 고르는 태도는 무엇인가요?","읽기에 흥미를 가지고 즐겨 읽는 태도"]],
  "produce":["첫 번째 글을 의미가 드러나도록 띄어 소리 내어 읽어 보세요.","인물의 마음과 나의 비슷하거나 다른 경험을 두 문장으로 써 보세요."],"model":"지우는 새싹을 보고 기뻤을 것입니다. 나도 심은 봉선화에서 싹이 났을 때 오래 바라보았습니다."},
 {"id":"korean-1-2-writing","band":"1-2","domain":"쓰기","module":"소개하고 겪은 일 쓰기","standards":codes(2,3,4),
  "a":["내 연필꽂이","내 책상에는 파란 연필꽂이가 있습니다.","연필꽂이는 둥글고 손바닥 두 개만큼 큽니다.","연필과 자를 한곳에 넣을 수 있어서 편리합니다.","나는 공부가 끝나면 연필을 꼭 제자리에 둡니다."],
  "qa":[["소개하는 대상은 무엇인가요?","연필꽂이"],["무슨 색인가요?","파란색"],["어떤 모양인가요?","둥근 모양"],["편리한 까닭은 무엇인가요?","연필과 자를 한곳에 넣을 수 있어서"]],
  "b":["처음 자전거를 탄 날","지난 토요일에 공원에서 두발자전거를 탔습니다.","처음에는 자꾸 한쪽으로 기울어졌습니다.","아버지가 뒤에서 잡아 주셔서 다시 힘껏 발을 굴렀습니다.","혼자 앞으로 나아가자 바람까지 나를 응원하는 것 같았습니다."],
  "qb":[["언제 있었던 일인가요?","지난 토요일"],["어디에서 자전거를 탔나요?","공원"],["누가 도와주었나요?","아버지"],["글쓴이의 느낌은 무엇인가요?","기쁘고 뿌듯하다."]],
  "focus":[["문장은 무엇으로 시작하나요?","알맞은 글자와 내용"],["문장 끝에는 무엇을 쓰나요?","문장 부호"],["소개 글에 넣을 내용을 두 가지 쓰세요.","생김새, 쓰임"],["겪은 일 글에 넣을 내용을 쓰세요.","언제·어디서·무슨 일·느낌"]],
  "produce":["내 주변 물건 하나를 골라 세 문장으로 소개하세요.","기억에 남는 일을 순서와 느낌이 드러나게 네 문장으로 쓰세요."],"model":"내 가방은 초록색입니다. 주머니가 세 개라서 물건을 나누어 넣기 좋습니다. 나는 매일 가방을 스스로 정리합니다."},
 {"id":"korean-1-2-grammar","band":"1-2","domain":"문법","module":"한글 소리와 문장 부호","standards":codes(2,4,3),
  "a":["소리와 글자","‘ㄴ’의 이름은 ‘니은’이고 소릿값은 [ㄴ]입니다.","‘나무’는 ㄴ, ㅏ, ㅁ, ㅜ가 모여 만들어진 말입니다.","글자의 이름과 소리를 알면 처음 보는 말도 또박또박 읽을 수 있습니다."],
  "qa":[["ㄴ의 이름은 무엇인가요?","니은"],["ㄴ의 소릿값은 무엇인가요?","[ㄴ]"],["나무의 첫 자음은 무엇인가요?","ㄴ"],["글자의 이름과 소리를 알면 무엇이 좋은가요?","처음 보는 말도 읽을 수 있다."]],
  "b":["문장 부호 탐정","“오늘은 어디에 갈까?” 하고 누나가 물었습니다.","나는 “동물원에 가고 싶어!” 하고 힘차게 대답했습니다.","물음표는 묻는 문장 끝에, 느낌표는 강한 느낌을 나타내는 문장 끝에 씁니다."],
  "qb":[["묻는 문장 끝의 부호는 무엇인가요?","물음표"],["강한 느낌을 나타내는 부호는 무엇인가요?","느낌표"],["‘오늘은 어디에 갈까’ 뒤의 부호를 쓰세요.","?"],["‘정말 멋지다’에 강한 느낌을 더해 쓰세요.","정말 멋지다!"]],
  "focus":[["[꼳]으로 소리 나지만 바른 표기는 무엇인가요?","꽃"],["[낟]으로 소리 나지만 바른 표기는 무엇인가요?","낮"],["알리는 문장 끝의 부호는 무엇인가요?","마침표"],["문장 첫 글자는 어떻게 쓰나요?","문장의 시작이 드러나게 바르게 쓴다."]],
  "produce":["좋아하는 낱말 하나를 자음과 모음으로 나누어 보세요.","물음표·느낌표·마침표가 하나씩 들어간 세 문장을 쓰세요."],"model":"구름: ㄱ, ㅜ, ㄹ, ㅡ, ㅁ / 오늘 하늘은 맑다. 어디로 갈까? 정말 신난다!"},
 {"id":"korean-1-2-literature","band":"1-2","domain":"문학","module":"말의 재미와 이야기 상상","standards":codes(2,5,4),
  "a":["빗방울 연주회","톡톡 창문을 두드리는 빗방울","또르르 유리 미끄럼을 타는 빗방울","첨벙 웅덩이 북을 치는 빗방울","오늘 골목은 빗방울 연주회"],
  "qa":[["빗방울이 창문을 두드리는 소리는 무엇인가요?","톡톡"],["유리에서 움직이는 모습은 무엇에 빗대었나요?","미끄럼"],["웅덩이를 무엇에 빗대었나요?","북"],["시를 읽고 떠오르는 느낌을 쓰세요.","즐겁고 경쾌하다."]],
  "b":["달팽이의 우산","달팽이는 비가 오자 커다란 버섯 아래로 갔습니다.","이미 개미 세 마리가 비를 피하고 있었습니다.","달팽이는 몸을 조금 접어 자리를 내주었습니다.","비가 그치자 모두 함께 무지개를 보았습니다."],
  "qb":[["달팽이는 어디로 갔나요?","버섯 아래"],["누가 먼저 있었나요?","개미 세 마리"],["달팽이가 한 행동은 무엇인가요?","몸을 접어 자리를 내주었다."],["달팽이의 마음을 짐작하세요.","함께 비를 피하고 싶은 배려하는 마음"]],
  "focus":[["말놀이에서 비슷한 소리를 반복하면 어떤 느낌이 드나요?","리듬과 재미가 생긴다."],["낭송할 때 살릴 것은 무엇인가요?","소리와 장면의 느낌"],["이야기 인물을 상상할 단서는 무엇인가요?","말, 행동, 사건"],["작품을 즐기는 방법을 하나 쓰세요.","낭송하기 / 그림으로 표현하기 / 생각 나누기"]],
  "produce":["‘사각사각’처럼 재미있는 소리를 넣어 두 줄 시를 지으세요.","달팽이의 다음 행동을 그림과 두 문장으로 표현하세요."],"model":"사각사각 연필이 걷는다. 하얀 종이 길 위에 생각 발자국을 남긴다."},
 {"id":"korean-1-2-media","band":"1-2","domain":"매체","module":"글과 그림으로 경험 표현하기","standards":codes(2,6,2),
  "a":["우리 주변의 매체","책은 글과 그림으로 이야기를 전합니다.","라디오는 소리로 소식과 음악을 들려줍니다.","영상은 움직이는 그림과 소리를 함께 보여 줍니다.","매체마다 생각을 전하는 방법이 다릅니다."],
  "qa":[["책이 사용하는 두 가지는 무엇인가요?","글과 그림"],["라디오는 무엇을 사용하나요?","소리"],["영상은 무엇을 함께 보여 주나요?","움직이는 그림과 소리"],["글의 중심 내용을 쓰세요.","매체마다 생각을 전하는 방법이 다르다."]],
  "b":["나의 하루 카드","아침: 창문을 열자 밝은 햇빛이 들어왔습니다.","낮: 친구와 운동장에서 공을 찼습니다.","저녁: 가족과 식탁에 둘러앉아 오늘 일을 이야기했습니다.","각 장면에 그림을 더하면 하루가 더 잘 떠오릅니다."],
  "qb":[["아침에 한 일은 무엇인가요?","창문을 열었다."],["낮에 누구와 무엇을 했나요?","친구와 공을 찼다."],["저녁에 가족과 무엇을 했나요?","오늘 일을 이야기했다."],["그림을 더하면 무엇이 좋은가요?","장면이 더 잘 떠오른다."]],
  "focus":[["글이 잘 전하는 것은 무엇인가요?","자세한 내용"],["그림이 잘 전하는 것은 무엇인가요?","모습과 분위기"],["소리가 잘 전하는 것은 무엇인가요?","목소리와 느낌"],["경험 카드에 필요한 두 요소는 무엇인가요?","글과 그림"]],
  "produce":["책·라디오·영상 중 관심 있는 매체와 까닭을 말하세요.","오늘의 한 장면을 짧은 글과 그림 계획으로 표현하세요."],"model":"장면: 비 온 뒤 운동장 / 글: 웅덩이에 구름이 비쳤다. / 그림: 파란 웅덩이와 하얀 구름"},

 {"id":"korean-3-4-listening-speaking","band":"3-4","domain":"듣기·말하기","module":"요약하고 의견 나누기","standards":codes(4,1,6),
  "a":["교실 식물 돌보기 안내","화분은 햇빛이 잘 드는 창가에 둡니다.","흙이 말랐는지 손가락으로 확인한 뒤 물을 줍니다.","잎에 먼지가 쌓이면 부드러운 천으로 닦습니다.","모둠별로 날짜를 정해 꾸준히 돌봅니다."],
  "qa":[["안내의 주제는 무엇인가요?","교실 식물 돌보기"],["물을 주기 전 확인할 것은 무엇인가요?","흙이 말랐는지"],["잎의 먼지는 무엇으로 닦나요?","부드러운 천"],["중요 내용을 한 문장으로 요약하세요.","모둠별로 정한 날짜에 식물 상태를 살펴 알맞게 돌본다."]],
  "b":["학급 쉬는 시간 토의","의견 가: 조용한 놀이 구역을 만들면 책이나 퍼즐을 좋아하는 친구가 편합니다.","의견 나: 공놀이 구역도 있어야 몸을 움직이고 싶은 친구가 즐겁습니다.","두 의견을 듣고 우리는 공간을 나누어 함께 사용하자고 정했습니다."],
  "qb":[["토의 주제는 무엇인가요?","쉬는 시간 공간 사용"],["의견 가의 이유는 무엇인가요?","조용한 놀이를 좋아하는 친구가 편해서"],["의견 나의 이유는 무엇인가요?","몸을 움직이고 싶은 친구가 즐거워서"],["결정한 해결 방법은 무엇인가요?","공간을 나누어 함께 사용한다."]],
  "focus":[["준언어 표현의 예는 무엇인가요?","목소리 크기, 빠르기, 억양"],["비언어 표현의 예는 무엇인가요?","표정, 몸짓, 시선"],["예의 있게 반대하는 표현을 쓰세요.","그 생각도 이해하지만 저는 다르게 생각합니다."],["발표 자료는 어떻게 정리하나요?","목적과 주제에 맞는 핵심 정보 중심으로"]],
  "produce":["첫 글을 30초 안에 요약해 발표하세요.","쉬는 시간 공간에 대한 내 의견과 이유를 말하고 다른 의견에 답하세요."],"model":"저는 공간을 나누어 쓰는 의견에 찬성합니다. 서로 다른 활동을 존중하면서 모두 안전하게 쉴 수 있기 때문입니다."},
 {"id":"korean-3-4-reading","band":"3-4","domain":"읽기","module":"중심 생각과 믿을 만한 출처","standards":codes(4,2,6),
  "a":["도시의 작은 숲","학교와 집 사이의 작은 공원에도 나무와 풀이 자랍니다.","이곳은 새와 곤충에게 먹이와 쉴 곳을 줍니다.","사람들은 그늘에서 쉬고 계절의 변화를 느낍니다.","작은 녹지라도 생물과 사람 모두에게 소중합니다."],
  "qa":[["첫 문단의 중심 대상은 무엇인가요?","작은 공원"],["동물에게 주는 도움은 무엇인가요?","먹이와 쉴 곳"],["사람에게 주는 도움은 무엇인가요?","그늘과 계절 변화"],["글의 중심 생각을 쓰세요.","작은 녹지도 생물과 사람에게 소중하다."]],
  "b":["자료 가와 자료 나","자료 가: 학교 과학관 누리집은 담당 기관과 작성 날짜를 밝히고 관찰 결과를 설명합니다.","자료 나: 작성자를 알 수 없는 게시물은 ‘무조건 맞다’고 주장하지만 근거와 날짜가 없습니다.","자료를 읽을 때에는 누가, 언제, 어떤 근거로 만들었는지 살펴야 합니다."],
  "qb":[["자료 가의 출처는 어디인가요?","학교 과학관 누리집"],["자료 나에서 빠진 것은 무엇인가요?","작성자, 근거, 날짜"],["더 믿을 만한 자료는 무엇인가요?","자료 가"],["판단 기준 세 가지를 쓰세요.","작성자, 날짜, 근거"]],
  "focus":[["사실은 무엇인가요?","확인할 수 있는 내용"],["의견은 무엇인가요?","생각이나 판단"],["읽기 전 예측에 쓰는 단서는 무엇인가요?","제목, 그림, 질문"],["읽은 뒤 점검할 것은 무엇인가요?","예측과 실제 내용, 이해하지 못한 부분"]],
  "produce":["첫 글을 문단별 중심 문장으로 간추리세요.","인터넷 자료 하나를 정해 출처의 신뢰성을 점검하는 질문을 만드세요."],"model":"누가 만들었는가? 언제 작성했는가? 근거와 출처가 제시되었는가? 다른 자료와 내용이 맞는가?"},
 {"id":"korean-3-4-writing","band":"3-4","domain":"쓰기","module":"문단과 목적에 맞는 글쓰기","standards":codes(4,3,5),
  "a":["종이 다리 실험 보고","목적: 종이 모양에 따라 버티는 힘이 달라지는지 알아본다.","절차: 평평한 종이와 접은 종이를 같은 간격의 책 위에 올린다.","결과: 접은 종이가 더 많은 지우개를 버텼다.","알게 된 점: 종이를 접으면 더 단단해질 수 있다."],
  "qa":[["실험 목적은 무엇인가요?","종이 모양과 버티는 힘의 관계 확인"],["비교한 종이 두 가지는 무엇인가요?","평평한 종이, 접은 종이"],["결과는 무엇인가요?","접은 종이가 더 많은 지우개를 버텼다."],["보고 글의 순서를 쓰세요.","목적 → 절차 → 결과 → 알게 된 점"]],
  "b":["고마운 마음을 전하는 글","지민아, 발표 연습을 할 때 내 말을 끝까지 들어줘서 고마워.","네가 고개를 끄덕여 준 덕분에 긴장이 줄었어.","다음 발표 준비 때에는 내가 네 연습을 도와줄게.","우리 서로 힘이 되어 주자."],
  "qb":[["글을 받는 사람은 누구인가요?","지민"],["고마운 일은 무엇인가요?","발표 연습을 끝까지 들어준 일"],["그 결과 어떤 변화가 있었나요?","긴장이 줄었다."],["글의 목적은 무엇인가요?","고마운 마음을 전하기"]],
  "focus":[["문단의 중심 내용을 담은 문장은 무엇인가요?","중심 문장"],["중심 문장을 자세히 설명하는 문장은 무엇인가요?","뒷받침 문장"],["의견 글에 필요한 두 요소는 무엇인가요?","의견, 이유"],["고쳐 쓸 때 살필 것은 무엇인가요?","문장과 문단의 연결, 정확한 표현"]],
  "produce":["학교에서 바꾸고 싶은 점에 대한 의견 문단을 쓰세요.","고마운 사람에게 구체적인 일과 마음이 드러나는 글을 쓰세요."],"model":"저는 교실에 종이 분리함을 더 놓아야 한다고 생각합니다. 종이를 다시 쓰거나 올바르게 버리기 쉬워지기 때문입니다."},
 {"id":"korean-3-4-grammar","band":"3-4","domain":"문법","module":"단어 관계와 알맞은 문장","standards":codes(4,4,5),
  "a":["단어의 관계","‘기쁘다’와 ‘즐겁다’는 뜻이 비슷합니다.","‘넓다’와 ‘좁다’는 뜻이 서로 반대입니다.","‘과일’은 ‘사과, 배, 감’보다 넓은 뜻을 가진 말입니다.","단어의 관계를 알면 뜻을 더 정확히 이해할 수 있습니다."],
  "qa":[["기쁘다와 뜻이 비슷한 말은 무엇인가요?","즐겁다"],["넓다와 뜻이 반대인 말은 무엇인가요?","좁다"],["사과·배·감을 포함하는 말은 무엇인가요?","과일"],["단어 관계를 알면 무엇이 좋은가요?","뜻을 더 정확히 이해할 수 있다."]],
  "b":["상황에 맞는 표현","할머니께서 방에 들어오십니다.","나는 친구에게 “이 책을 먼저 읽어. 그리고 나에게 알려 줘.”라고 말했습니다.","‘이’는 가까운 대상을 가리키고, ‘그리고’는 내용을 이어 줍니다.","말하는 상대와 상황에 따라 높임 표현을 알맞게 사용합니다."],
  "qb":[["높임 표현이 쓰인 말은 무엇인가요?","들어오십니다"],["가까운 대상을 가리키는 말은 무엇인가요?","이"],["내용을 이어 주는 말은 무엇인가요?","그리고"],["높임 표현은 무엇을 고려하나요?","상대와 상황"]],
  "focus":[["‘새가 난다’에서 ‘새가’의 역할은 무엇인가요?","누가에 해당하는 부분"],["‘새가 난다’에서 ‘난다’의 역할은 무엇인가요?","무엇을 한다에 해당하는 부분"],["국어사전에서 단어를 찾을 때 무엇을 기준으로 하나요?","첫 글자부터 자모 순서"],["언어는 관계 형성에 어떤 역할을 하나요?","마음과 생각을 주고받게 한다."]],
  "produce":["비슷한 말·반대말·포함 관계의 예를 하나씩 찾으세요.","친구와 어른에게 같은 내용을 각각 알맞게 말하는 문장을 쓰세요."],"model":"친구에게: 이 책 좀 봐. / 선생님께: 선생님, 이 책을 봐 주세요."},
 {"id":"korean-3-4-literature","band":"3-4","domain":"문학","module":"이야기 흐름과 감각적 표현","standards":codes(4,5,5),
  "a":["바람이 두고 간 편지","아침 바람이 창문을 살짝 두드렸습니다.","수아가 창문을 열자 은행잎 한 장이 책상 위로 날아왔습니다.","수아는 노란 잎맥을 손끝으로 따라가며 가을이 보낸 편지라고 생각했습니다.","그날 수아는 잎을 책갈피에 고이 넣었습니다."],
  "qa":[["주인공은 누구인가요?","수아"],["은행잎은 어디로 왔나요?","책상 위"],["수아는 은행잎을 무엇이라고 생각했나요?","가을이 보낸 편지"],["이야기의 흐름을 세 단계로 쓰세요.","바람이 창문을 두드림 → 잎이 날아옴 → 책갈피에 넣음"]],
  "b":["겨울 아침","하얀 입김이 몽글몽글 피어난다.","발밑 눈은 뽀드득 작은 북을 친다.","차가운 바람이 두 볼을 콕콕 찌른다.","나는 목도리 속에 웃음을 폭 감춘다."],
  "qb":[["눈 밟는 소리를 나타낸 말은 무엇인가요?","뽀드득"],["바람이 볼에 닿는 느낌은 무엇인가요?","콕콕 찌르는 듯한 느낌"],["시각을 나타내는 표현은 무엇인가요?","하얀 입김"],["시의 분위기를 쓰세요.","춥지만 즐겁고 생생하다."]],
  "focus":[["현실과 작품 속 세계를 비교할 때 떠올릴 것은 무엇인가요?","나의 비슷한 경험"],["작품을 소개할 때 필요한 것은 무엇인가요?","제목, 마음에 든 부분, 까닭"],["감각적 표현은 어떤 감각을 활용하나요?","시각·청각·촉각 등"],["작품을 즐겨 감상하는 태도의 예는 무엇인가요?","읽고 느낀 점을 나누거나 다시 읽기"]],
  "produce":["첫 이야기와 비슷한 나의 경험을 말하세요.","겨울 장면을 감각적 표현 두 가지 이상으로 네 줄 시로 쓰세요."],"model":"찬 공기가 코끝을 간질인다. / 얼음은 햇빛을 받아 반짝인다. / 발걸음마다 사각사각 / 겨울 길이 노래한다."},
 {"id":"korean-3-4-media","band":"3-4","domain":"매체","module":"자료를 찾고 바르게 공유하기","standards":codes(4,6,3),
  "a":["발표 자료 찾기","주제가 ‘우리 지역의 나무’라면 먼저 필요한 정보를 정합니다.","공공기관이나 도서관 누리집에서 자료를 찾습니다.","작성자와 날짜를 확인하고 주제에 맞는 내용만 선택합니다.","선택한 자료의 출처를 기록합니다."],
  "qa":[["가장 먼저 할 일은 무엇인가요?","필요한 정보 정하기"],["어디에서 자료를 찾나요?","공공기관이나 도서관 누리집"],["확인할 두 가지는 무엇인가요?","작성자, 날짜"],["선택한 뒤 기록할 것은 무엇인가요?","출처"]],
  "b":["한 장 발표 자료","제목은 발표 주제를 짧고 분명하게 보여 줍니다.","사진이나 그림은 핵심 내용을 이해하는 데 도움을 줍니다.","글자는 뒤에서도 읽을 수 있게 크게 씁니다.","다른 사람의 자료는 출처를 밝히고 허락된 범위에서 사용합니다."],
  "qb":[["제목은 어떻게 쓰나요?","짧고 분명하게"],["사진이나 그림의 역할은 무엇인가요?","핵심 내용 이해를 돕는다."],["글자는 왜 크게 쓰나요?","뒤에서도 읽을 수 있게"],["다른 사람 자료를 쓸 때 지킬 것은 무엇인가요?","출처와 이용 범위"]],
  "focus":[["검색어는 어떻게 정하나요?","주제의 핵심 낱말로"],["발표 자료 한 장에 정보를 너무 많이 넣으면 어떤가요?","핵심이 흐려진다."],["온라인에서 친구 사진을 공유하기 전 필요한 것은 무엇인가요?","친구의 동의"],["매체 소통 윤리의 핵심은 무엇인가요?","출처·개인정보·상대 존중"]],
  "produce":["‘우리 학교의 좋은 점’ 발표에 필요한 검색어와 자료 출처를 계획하세요.","제목·핵심 문장·그림 설명·출처가 있는 한 장 발표 자료를 설계하세요."],"model":"제목: 우리 학교의 작은 숲 / 핵심: 나무 18그루가 그늘과 쉼터를 만든다. / 출처: 학교 생태 조사표(2026)"},

 {"id":"korean-5-6-listening-speaking","band":"5-6","domain":"듣기·말하기","module":"질문하고 근거로 토론하기","standards":codes(6,1,7),
  "a":["학교 방송 면담","진행자: 도서관 이용 학생이 늘어난 까닭은 무엇인가요?","사서: 학생 추천 책 전시와 점심시간 독서 모임을 시작했기 때문입니다.","진행자: 앞으로 새롭게 해 보고 싶은 활동은 무엇인가요?","사서: 학생이 직접 책 소개 영상을 만드는 활동을 계획하고 있습니다."],
  "qa":[["면담 주제는 무엇인가요?","도서관 이용과 활동"],["이용 학생이 늘어난 까닭은 무엇인가요?","추천 책 전시와 독서 모임"],["앞으로 계획한 활동은 무엇인가요?","책 소개 영상 만들기"],["추가로 물을 질문을 만드세요.","책 소개 영상은 어디에 공개하나요? 등"]],
  "b":["휴대 전화 보관 토론","주장 가: 수업 중에는 휴대 전화를 한곳에 보관해야 합니다. 알림 때문에 집중이 흐트러질 수 있습니다.","주장 나: 학습에 필요한 때에는 교사의 안내에 따라 사용할 수 있어야 합니다. 검색과 촬영에 도움이 됩니다.","두 주장은 모두 수업 집중과 학습 효과를 중요하게 생각합니다."],
  "qb":[["주장 가의 근거는 무엇인가요?","알림이 집중을 흐트러뜨릴 수 있다."],["주장 나의 근거는 무엇인가요?","검색과 촬영이 학습에 도움 된다."],["두 주장의 공통 관심은 무엇인가요?","수업 집중과 학습 효과"],["조정안을 쓰세요.","평소에는 보관하고 교사 안내가 있을 때만 사용한다."]],
  "focus":[["생략된 내용을 추론할 때 무엇을 살피나요?","앞뒤 말과 상황"],["면담 전에 준비할 것은 무엇인가요?","목적, 상대 정보, 질문"],["토의에서 의견 조정은 무엇인가요?","공통점과 차이를 찾아 해결안을 만드는 것"],["토론 근거는 어떠해야 하나요?","주장과 관련 있고 믿을 만하며 타당해야 한다."]],
  "produce":["도서관 면담 질문을 목적에 맞게 세 개 더 만드세요.","휴대 전화 사용 주제로 주장·근거·예상 반론·답변을 준비해 토론하세요."],"model":"주장: 교사의 안내가 있을 때만 사용해야 한다. 근거: 학습 도구로 활용하면서 불필요한 알림은 줄일 수 있다."},
 {"id":"korean-5-6-reading","band":"5-6","domain":"읽기","module":"구조를 읽고 관점 평가하기","standards":codes(6,2,5),
  "a":["빗물 정원의 원리","빗물 정원은 비가 올 때 물을 잠시 모아 두는 낮은 공간입니다.","먼저 지붕과 길에서 흐른 빗물이 정원으로 들어옵니다.","그다음 흙과 식물 뿌리가 물을 천천히 흡수하고 일부 오염 물질을 거릅니다.","따라서 빗물 정원은 침수를 줄이고 생물의 작은 터전도 만듭니다."],
  "qa":[["빗물 정원은 무엇인가요?","빗물을 잠시 모아 두는 낮은 공간"],["물이 들어온 뒤 무엇이 흡수하나요?","흙과 식물 뿌리"],["두 가지 효과를 쓰세요.","침수 감소, 생물 터전 조성"],["글의 구조에 맞게 요약하세요.","정의 → 작동 과정 → 효과"]],
  "b":["운동장 나무 심기 두 관점","관점 가: 나무를 심으면 그늘과 쉼터가 생기고 여름 운동장 온도를 낮출 수 있습니다.","관점 나: 경기 공간이 줄고 뿌리가 달리기를 방해하지 않도록 위치와 종류를 신중히 정해야 합니다.","문제를 해결하려면 장점과 우려를 함께 살펴 심을 장소와 수종을 결정해야 합니다."],
  "qb":[["관점 가가 강조한 장점은 무엇인가요?","그늘·쉼터·온도 감소"],["관점 나가 걱정한 점은 무엇인가요?","경기 공간과 뿌리 안전"],["두 관점을 함께 고려한 해결 방법은 무엇인가요?","경기를 방해하지 않는 곳에 알맞은 수종을 심는다."],["글의 표현이 타당한 까닭은 무엇인가요?","두 관점의 이유를 구체적으로 제시했기 때문"]],
  "focus":[["함축된 표현은 어떻게 추론하나요?","문맥과 앞뒤 단서로"],["주장은 무엇인가요?","글쓴이가 옳다고 내세우는 생각"],["타당성 평가 기준은 무엇인가요?","근거의 관련성·충분성·신뢰성"],["적극적 읽기의 예는 무엇인가요?","질문하고 메모하며 다른 자료와 연결하기"]],
  "produce":["첫 글을 70자 안으로 요약하세요.","두 관점을 비교한 뒤 가장 타당한 해결안을 근거와 함께 쓰세요."],"model":"운동장 가장자리에 뿌리가 깊게 퍼지지 않는 나무를 심자. 경기 공간과 안전을 지키면서 그늘을 만들 수 있다."},
 {"id":"korean-5-6-writing","band":"5-6","domain":"쓰기","module":"설명하고 근거로 주장하기","standards":codes(6,3,6),
  "a":["도서관 자동 대출기의 특징","자동 대출기는 학생이 스스로 책을 빌리고 반납하도록 돕는 기기입니다.","화면의 안내에 따라 학생증과 책의 바코드를 차례로 인식합니다.","대출 결과를 바로 확인할 수 있어 기다리는 시간을 줄입니다.","다만 오류가 나면 사서에게 도움을 요청해야 합니다."],
  "qa":[["설명 대상은 무엇인가요?","도서관 자동 대출기"],["사용 순서를 쓰세요.","화면 안내 → 학생증 인식 → 책 바코드 인식 → 결과 확인"],["장점은 무엇인가요?","기다리는 시간을 줄인다."],["주의할 점은 무엇인가요?","오류가 나면 사서에게 도움을 요청한다."]],
  "b":["학교 물병 사용 제안","주장: 학교에서 개인 물병 사용을 늘려야 합니다.","근거 1: 일회용 컵 사용량을 줄일 수 있습니다. 우리 반 일주일 조사에서 일회용 컵 86개가 사용되었습니다.","근거 2: 물을 자주 마시는 습관을 기르는 데 도움이 됩니다.","출처: 6학년 2반 생활 조사표, 2026년 7월."],
  "qb":[["글의 주장은 무엇인가요?","개인 물병 사용을 늘려야 한다."],["수치가 있는 근거는 무엇인가요?","일주일에 일회용 컵 86개 사용"],["근거의 출처는 무엇인가요?","6학년 2반 생활 조사표"],["출처를 밝히는 까닭은 무엇인가요?","근거의 출처와 신뢰성을 확인하게 하려고"]],
  "focus":[["설명 글의 내용 선정 기준은 무엇인가요?","대상의 특성과 독자에게 필요한 정보"],["주장 글의 근거는 어떠해야 하나요?","주장과 관련 있고 믿을 만해야 한다."],["글 전체를 고칠 때 살필 것은 무엇인가요?","주제의 통일성, 문단 순서, 표현"],["공유 전 고려할 것은 무엇인가요?","독자, 매체, 개인정보, 출처"]],
  "produce":["학교 시설 하나를 골라 특징과 사용 방법을 설명하세요.","학교생활 개선 주장을 정하고 근거 두 개와 출처를 밝혀 글을 쓰세요."],"model":"주장: 빈 교실의 불을 꺼야 한다. 근거: 에너지를 아끼고 불필요한 전력 사용을 줄인다. 출처: 학교 에너지 절약 안내문(2026)."},
 {"id":"korean-5-6-grammar","band":"5-6","domain":"문법","module":"언어 다양성과 바른 문장","standards":codes(6,4,6),
  "a":["표준어와 방언","표준어는 서로 다른 지역의 사람들이 널리 소통하는 데 도움을 줍니다.","방언은 지역의 역사와 생활 모습을 담고 있으며 같은 지역 사람 사이의 친밀감을 높이기도 합니다.","어느 한쪽이 더 우수한 것이 아니라 상황과 공동체에 따라 기능이 다릅니다."],
  "qa":[["표준어의 기능은 무엇인가요?","넓은 지역의 소통을 돕는다."],["방언이 담는 것은 무엇인가요?","지역의 역사와 생활 모습"],["방언의 관계 기능은 무엇인가요?","친밀감을 높이기도 한다."],["두 언어의 관계를 어떻게 보아야 하나요?","상황과 공동체에 따라 기능이 다르다."]],
  "b":["문장 고쳐 쓰기","‘나는 결코 약속을 꼭 잊지 않겠다.’는 부사어의 호응이 어색합니다.","‘결코’는 보통 ‘않다’나 ‘없다’와 어울립니다.","따라서 ‘나는 약속을 결코 잊지 않겠다.’로 고치면 자연스럽습니다.","문장 성분과 호응을 살피면 뜻을 분명하게 전할 수 있습니다."],
  "qb":[["어색한 까닭은 무엇인가요?","부사어의 호응이 맞지 않아서"],["결코와 어울리는 표현은 무엇인가요?","않다 / 없다"],["바르게 고친 문장을 쓰세요.","나는 약속을 결코 잊지 않겠다."],["호응을 살피면 무엇이 좋은가요?","뜻을 분명히 전할 수 있다."]],
  "focus":[["‘발이 넓다’의 관용적 뜻은 무엇인가요?","아는 사람이 많다."],["‘어제 읽는다’를 바르게 고치세요.","어제 읽었다."],["음성 언어의 특징은 무엇인가요?","목소리·억양·표정과 함께 전달된다."],["문자 언어의 특징은 무엇인가요?","기록되어 다시 읽고 고칠 수 있다."]],
  "produce":["가족이나 지역에서 쓰는 방언을 하나 조사해 뜻과 쓰임을 적으세요.","호응·시간 표현·띄어쓰기가 어색한 문장을 찾아 바르게 고치세요."],"model":"고치기 전: 나는 내일 도서관에 갔다. / 고친 뒤: 나는 내일 도서관에 갈 것이다."},
 {"id":"korean-5-6-literature","band":"5-6","domain":"문학","module":"작가의 의도와 삶의 성찰","standards":codes(6,5,6),
  "a":["빈 의자","운동장 끝 느티나무 아래에는 낡은 의자 하나가 있었습니다.","친구와 다툰 현우는 혼자 그 의자에 앉아 운동화를 바라보았습니다.","잠시 뒤 친구가 말없이 옆에 앉아 반으로 나눈 귤을 건넸습니다.","현우는 귤 한 쪽을 받아 들고 의자의 빈틈이 조금 줄었다고 느꼈습니다."],
  "qa":[["배경은 어디인가요?","운동장 끝 느티나무 아래"],["현우가 혼자 있던 까닭은 무엇인가요?","친구와 다퉈서"],["친구는 어떻게 화해의 뜻을 보였나요?","옆에 앉아 귤을 건넸다."],["‘의자의 빈틈이 줄었다’가 뜻하는 것은 무엇인가요?","두 사람의 마음의 거리가 가까워졌다."]],
  "b":["등불","작은 친절은 어둔 길의 등불 같다.","눈부시게 세상을 다 밝히지는 못해도","바로 곁 한 사람의 발밑을 비추고","그 빛이 또 다른 등불을 깨운다."],
  "qb":[["작은 친절을 무엇에 비유했나요?","등불"],["등불이 비추는 곳은 어디인가요?","곁에 있는 한 사람의 발밑"],["마지막 행의 뜻을 쓰세요.","친절이 다른 친절로 이어진다."],["비유의 효과는 무엇인가요?","친절의 가치와 퍼지는 모습을 생생하게 느끼게 한다."]],
  "focus":[["소설의 세 요소는 무엇인가요?","인물, 사건, 배경"],["작가의 의도를 짐작할 단서는 무엇인가요?","인물의 변화, 반복 표현, 사건의 결말"],["작품 의견에는 무엇이 필요한가요?","인상적인 부분과 그렇게 생각한 까닭"],["삶과 연관 지어 성찰한다는 뜻은 무엇인가요?","작품을 내 경험과 선택에 비추어 생각하는 것"]],
  "produce":["첫 작품에서 작가가 전하고 싶은 생각을 근거와 함께 쓰세요.","나의 경험을 시·소설·극·수필 중 알맞은 갈래로 짧게 표현하세요."],"model":"작가는 먼저 다가가는 작은 행동이 관계를 회복할 수 있음을 전하려 했다. 친구가 말 대신 귤을 건네자 현우가 마음의 거리가 줄었다고 느꼈기 때문이다."},
 {"id":"korean-5-6-media","band":"5-6","domain":"매체","module":"정보 신뢰성과 책임 있는 제작","standards":codes(6,6,4),
  "a":["두 온라인 자료 비교","자료 가는 국립 기상 기관이 오늘 오전 9시에 발표했으며 측정 방법과 지역별 수치를 제시합니다.","자료 나는 작성자와 날짜가 없고 ‘올해는 역사상 가장 더울 것’이라고만 주장합니다.","정보를 고를 때에는 작성 주체, 최신성, 근거, 다른 자료와의 일치 여부를 살펴야 합니다."],
  "qa":[["자료 가의 작성 주체는 누구인가요?","국립 기상 기관"],["자료 가가 제시한 근거 형태는 무엇인가요?","측정 방법과 지역별 수치"],["자료 나에서 빠진 정보는 무엇인가요?","작성자, 날짜, 근거"],["더 신뢰할 만한 자료와 까닭을 쓰세요.","자료 가. 작성 주체·날짜·근거가 분명해서"]],
  "b":["복합양식 안전 캠페인","수용자가 저학년이라면 짧은 문장과 쉬운 그림을 사용합니다.","핵심 행동은 큰 제목과 순서 그림으로 보여 줍니다.","배경 음악이나 효과음은 내용을 방해하지 않게 사용합니다.","완성한 자료는 친구 반응을 확인하고 고친 뒤 출처와 함께 공유합니다."],
  "qb":[["수용자는 누구인가요?","저학년 학생"],["문장과 그림은 어떻게 하나요?","짧고 쉽게"],["핵심 행동은 어떻게 보여 주나요?","큰 제목과 순서 그림"],["공유 전에 할 일은 무엇인가요?","친구 반응을 확인해 고치고 출처를 밝힌다."]],
  "focus":[["검색어를 좁히는 방법은 무엇인가요?","핵심어에 지역·기간·자료 종류를 더한다."],["뉴스 신뢰성 평가 기준을 쓰세요.","작성 주체·날짜·근거·출처·다른 자료와의 일치"],["복합양식 자료란 무엇인가요?","글·그림·소리·영상 등을 함께 사용한 자료"],["매체 이용 성찰 질문을 하나 쓰세요.","나는 목적 없이 너무 오래 사용하지 않았는가? 등"]],
  "produce":["같은 주제의 온라인 자료 두 개를 찾아 신뢰성을 비교하는 계획을 세우세요.","대상과 매체를 정해 안전 캠페인 한 장 자료의 구성안을 만드세요."],"model":"대상: 1학년 / 매체: 교실 포스터 / 핵심 행동: 계단에서 걷기 / 구성: 큰 제목, 세 단계 그림, 짧은 설명, 출처"},
]

PILOT_UNIT_IDS={"korean-1-2-listening-speaking","korean-3-4-writing","korean-5-6-reading"}
READING_TIPS={
 "korean-5-6-reading":{
  "a":"정의 → 작동 과정 → 효과와 한계를 표시하며 읽으세요.",
  "b":"주장·근거·우려를 비교하며 읽으세요."
 }
}

W,H,M=1024,1536,72
C={"paper":"#FFFCF5","ink":"#2E2740","muted":"#685F74","brand":"#62406F","coral":"#E97863","teal":"#3E8276","line":"#D8CEDB","cream":"#FFF0D5","mint":"#E1F0EA","lav":"#EEE7F4"}
FONT="Apple SD Gothic Neo, Noto Sans KR, sans-serif"
def esc(v:Any)->str:return html.escape(str(v),quote=True)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(v:str,x:float,y:float,size:int,color:str=C["ink"],weight:int=500,anchor:str="start")->str:return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(v)}</text>'
def wrap(v:str,limit:int)->list[str]:
    words=v.split(); lines=[]; cur=""
    for word in words:
        trial=f"{cur} {word}".strip()
        if len(trial)>limit and cur:lines.append(cur);cur=word
        else:cur=trial
    if cur:lines.append(cur)
    return lines
def para(v:str,x:int,y:int,size:int,limit:int,lh:int,color:str=C["ink"],weight:int=500)->str:
    lines=wrap(v,limit); spans="".join(f'<tspan x="{x}" dy="{0 if i==0 else lh}">{esc(line)}</tspan>' for i,line in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}">{spans}</text>'
def shell(u:dict[str,Any],page:int,label:str)->list[str]:
    return ['<?xml version="1.0" encoding="UTF-8"?>',f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="{C["paper"]}"/>',f'<rect width="{W}" height="184" fill="{C["brand"]}"/>',txt("초등 국어 한 장",M,54,21,"#FFF",700),txt(u["module"],M,108,38,"#FFF",800),txt(f'{u["band"]}학년군 · {u["domain"]} · {label}',M,151,20,"#FFF",600),txt(str(page),W-M,151,21,"#FFF",700,"end")]
def footer(p:list[str])->None:
    p += [f'<line x1="{M}" y1="1460" x2="{W-M}" y2="1460" stroke="{C["line"]}" stroke-width="2"/>',txt("Taehyeong Lim · CC BY-NC-SA 4.0",M,1495,15,C["muted"],600),txt("표지 이미지: GPT Image · Gongnyang Prompt Kit",W-M,1495,15,C["muted"],500,"end"),"</svg>"]
def cover(u:dict[str,Any])->str:
    data=base64.b64encode((ROOT/"assets"/"cover-masters"/f'korean-{u["band"]}.png').read_bytes()).decode()
    standards=" ".join(u["standards"])
    return "\n".join(['<?xml version="1.0" encoding="UTF-8"?>',f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 {W} {H}">',f'<image href="data:image/png;base64,{data}" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>','<rect x="54" y="54" width="916" height="196" rx="24" fill="#FFFCF5" opacity=".95"/>',txt("초등 국어 한 장",86,112,28,C["brand"],800),txt(f'{u["band"]}학년군 · {u["domain"]}',86,158,19,C["muted"],700),para(standards,86,203,16,70,22,C["muted"],650),'<rect x="54" y="1130" width="916" height="332" rx="24" fill="#FFFCF5" opacity=".96"/>',para(u["module"],86,1214,43,22,55,C["brand"],800),txt("읽기 · 탐구 · 표현 · 성찰",86,1325,18,C["coral"],800),txt("Taehyeong Lim · CC BY-NC-SA 4.0",86,1380,16,C["brand"],700),txt("이미지 제작: GPT Image · Gongnyang Prompt Kit",86,1418,16,C["brand"],700),"</svg>"])
def reading(u:dict[str,Any],page:int,key:str,title_label:str)->str:
    data=u[key]; p=shell(u,page,title_label); p += [txt("ORIGINAL TEXT",M,240,18,C["coral"],800),txt(data[0],M,286,31,C["brand"],800),f'<rect x="{M}" y="330" width="{W-2*M}" height="900" rx="24" fill="#FFF" stroke="{C["line"]}" stroke-width="2"/>']
    for i,line in enumerate(data[1:]):p.append(para(line,M+38,405+i*135,27,45,37,C["ink"],620))
    tip=READING_TIPS.get(u["id"],{}).get(key,"핵심 낱말에 표시하고, 인물·사건·정보의 관계를 생각하며 두 번 읽으세요.")
    p += [f'<rect x="{M}" y="1260" width="{W-2*M}" height="124" rx="20" fill="{C["mint"]}"/>',txt("읽기 도움",M+26,1302,17,C["teal"],800),para(tip,M+26,1340,21,54,29,C["ink"],600)]
    footer(p); return "\n".join(p)
def questions(u:dict[str,Any],page:int,key:str,label:str)->str:
    p=shell(u,page,label); p += [txt("생각 확인",M,245,31,C["brand"],800)]
    items=u[key]
    if len(items)<=4:
        for i,(q,a) in enumerate(items):
            y=300+i*250; p += [f'<rect x="{M}" y="{y}" width="{W-2*M}" height="218" rx="22" fill="#FFF" stroke="{C["line"]}" stroke-width="2"/>',f'<circle cx="{M+30}" cy="{y+42}" r="25" fill="{C["coral"]}"/>',txt(str(i+1),M+30,y+51,24,"#FFF",800,"middle"),para(q,M+78,y+52,23,52,32,C["ink"],680)]
            for n in range(3):p.append(f'<line x1="{M+36}" y1="{y+120+n*34}" x2="{W-M-32}" y2="{y+120+n*34}" stroke="{C["line"]}" stroke-width="2"/>')
    else:
        # Five and six question pages use a two-column compact grid so every
        # prompt and answer area remains above the footer.
        gap=28; card_w=(W-2*M-gap)//2; card_h=310
        for i,(q,a) in enumerate(items):
            col=i%2; row=i//2; x=M+col*(card_w+gap); y=300+row*(card_h+22)
            p += [f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="22" fill="#FFF" stroke="{C["line"]}" stroke-width="2"/>',f'<circle cx="{x+29}" cy="{y+40}" r="23" fill="{C["coral"]}"/>',txt(str(i+1),x+29,y+48,22,"#FFF",800,"middle"),para(q,x+66,y+47,20,25,28,C["ink"],680)]
            for n in range(3):p.append(f'<line x1="{x+26}" y1="{y+205+n*31}" x2="{x+card_w-26}" y2="{y+205+n*31}" stroke="{C["line"]}" stroke-width="2"/>')
    footer(p); return "\n".join(p)
def focus_page(u:dict[str,Any])->str:
    p=shell(u,6,"개념 탐구"); p += [txt("LANGUAGE & LITERACY",M,242,18,C["coral"],800),txt("성취기준 핵심을 확인하세요.",M,286,29,C["brand"],800)]
    for i,(q,a) in enumerate(u["focus"]):
        y=342+i*240;p += [f'<rect x="{M}" y="{y}" width="{W-2*M}" height="205" rx="22" fill="{C["lav"] if i%2==0 else C["mint"]}"/>',txt(f"{i+1}.",M+28,y+50,24,C["brand"],800),para(q,M+78,y+50,22,52,30,C["ink"],700),txt("내 답",M+78,y+113,16,C["muted"],700),f'<line x1="{M+140}" y1="{y+116}" x2="{W-M-35}" y2="{y+116}" stroke="{C["line"]}" stroke-width="2"/>',f'<line x1="{M+78}" y1="{y+158}" x2="{W-M-35}" y2="{y+158}" stroke="{C["line"]}" stroke-width="2"/>']
    footer(p);return "\n".join(p)
def production(u:dict[str,Any])->str:
    p=shell(u,7,"표현·성찰");p += [txt("APPLY & REFLECT",M,242,18,C["coral"],800),txt("읽고 생각한 내용을 나의 말과 글로 표현하세요.",M,286,29,C["brand"],800)]
    for i,prompt in enumerate(u["produce"]):
        y=350+i*380;p += [f'<rect x="{M}" y="{y}" width="{W-2*M}" height="330" rx="24" fill="{C["mint"] if i==0 else "#FFF"}" stroke="{C["line"]}" stroke-width="2"/>',txt(f'{i+1}. {"말하기" if i==0 else "쓰기"}',M+28,y+48,18,C["coral"],800),para(prompt,M+28,y+94,24,52,33,C["ink"],700)]
        for n in range(5):p.append(f'<line x1="{M+30}" y1="{y+170+n*32}" x2="{W-M-30}" y2="{y+170+n*32}" stroke="{C["line"]}" stroke-width="2"/>')
    p += [f'<rect x="{M}" y="1130" width="{W-2*M}" height="235" rx="22" fill="{C["cream"]}"/>',txt("예시",M+28,1176,18,C["brand"],800),para(u["model"],M+28,1223,21,56,30,C["ink"],650)]
    footer(p);return "\n".join(p)
def answers(u:dict[str,Any])->str:
    p=shell(u,8,"정답·예시"); p += [txt("정답과 확인 기준",M,242,31,C["brand"],800)]
    groups=[("첫 글",u["qa"]),("둘째 글",u["qb"]),("개념 탐구",u["focus"])]
    y=290
    for title,items in groups:
        p += [txt(title,M,y,19,C["coral"],800)];y+=42
        for i,(_,a) in enumerate(items):
            p += [txt(f"{i+1}.",M,y,18,C["brand"],800),para(a,M+42,y,18,68,25,C["ink"],600)];y+=58 if len(a)<48 else 78
        y+=18
    p += [f'<rect x="{M}" y="1245" width="{W-2*M}" height="140" rx="18" fill="{C["cream"]}"/>',txt("표현 활동",M+24,1285,17,C["brand"],800),para("예시는 한 가지 답입니다. 글의 근거를 활용하고 활동 조건에 맞게 표현했다면 알맞은 답으로 봅니다.",M+24,1324,18,66,26,C["ink"],600)]
    footer(p);return "\n".join(p)
def raster(svg:Path,webp:Path)->None:
    png=webp.with_suffix(".png");subprocess.run(["node",str(ROOT/"scripts"/"rasterize-svg.mjs"),str(svg),str(png),str(webp)],cwd=ROOT,check=True);png.unlink()
def pdf(workbook:dict[str,Any])->None:
    target=PUBLIC/workbook["pdf"]["path"].lstrip("/");doc=canvas.Canvas(str(target),pagesize=A4,pageCompression=1);doc.setTitle(workbook["title"]);doc.setAuthor(workbook["author"]);doc.setSubject(" · ".join(workbook["standardCodes"]));doc.setCreator("초등 국어 한 장 deterministic renderer")
    for page in workbook["pages"]:doc.drawImage(ImageReader(Image.open(PUBLIC/page["imagePath"].lstrip("/"))),0,0,A4[0],A4[1],mask="auto");doc.showPage()
    doc.save()
def transcript(u:dict[str,Any],w:dict[str,Any])->str:
    def section(title,key):return f"<h2>{title}</h2><h3>{esc(u[key][0])}</h3>"+''.join(f"<p>{esc(x)}</p>" for x in u[key][1:])
    def qs(title,key):return f"<h2>{title}</h2><ol>"+''.join(f"<li>{esc(q)} <strong>정답: {esc(a)}</strong></li>" for q,a in u[key])+"</ol>"
    return f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>{esc(w['title'])} 전문</title></head><body><main><h1>{esc(w['title'])}</h1><p>{' '.join(w['standardCodes'])}</p>{section('첫 글','a')}{qs('첫 글 확인','qa')}{section('둘째 글','b')}{qs('둘째 글 확인','qb')}{qs('개념 탐구','focus')}<h2>표현·성찰</h2><p>{esc(u['produce'][0])}</p><p>{esc(u['produce'][1])}</p><p><strong>예시:</strong> {esc(u['model'])}</p></main></body></html>\n"
def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--unit",action="append");parser.add_argument("--pilot",action="store_true");parser.add_argument("--preserve-covers",action="store_true");args=parser.parse_args()
    if args.pilot and args.unit:raise ValueError("Use --pilot or --unit, not both")
    selected=PILOT_UNIT_IDS if args.pilot else set(args.unit or []);preserve_covers=args.preserve_covers or args.pilot;units=[u for u in UNITS if not selected or u["id"] in selected]
    missing=selected-{u["id"] for u in units}
    if missing:raise ValueError(f"Unknown units: {missing}")
    cp=CONTENT/"catalog.json";cat=json.loads(cp.read_text());existing_by_id={workbook["id"]:workbook for workbook in cat["workbooks"]}
    for source in (CONTENT/"workbooks").glob("*.json"):
        current=json.loads(source.read_text(encoding="utf-8"));existing_by_id[current["id"]]=current
    replace={u["id"] for u in units};cat["workbooks"]=[w for w in cat["workbooks"] if w["id"] not in replace]
    for u in units:
        slug=u["id"];out=PUBLIC/"workbooks"/slug;sd=SVG_ROOT/slug;out.mkdir(parents=True,exist_ok=True);sd.mkdir(parents=True,exist_ok=True)
        current=existing_by_id.get(slug,{});activities=current.get("activities")
        if "gradeBand" in current:u={**u,"band":current["gradeBand"]}
        if "standardCodes" in current:u={**u,"standards":current["standardCodes"]}
        if "domain" in current:u={**u,"domain":current["domain"]}
        if "module" in current:u={**u,"module":current["module"]}
        if isinstance(activities,dict):
            u={**u,
               **({"a":activities["textA"]} if "textA" in activities else {}),
               **({"qa":activities["questionsA"]} if "questionsA" in activities else {}),
               **({"b":activities["textB"]} if "textB" in activities else {}),
               **({"qb":activities["questionsB"]} if "questionsB" in activities else {}),
               **{key:activities[key] for key in ("focus","produce","model") if key in activities}}
        sources=[cover(u),reading(u,2,"a","첫 글 읽기"),questions(u,3,"qa","첫 글 탐구"),reading(u,4,"b","둘째 글 읽기"),questions(u,5,"qb","둘째 글 탐구"),focus_page(u),production(u),answers(u)]
        names=["01-cover","02-reading-a","03-questions-a","04-reading-b","05-questions-b","06-focus","07-production","08-answers"];roles=["cover"]+["worksheet"]*6+["answer"];pages=[]
        for i,(name,source,role) in enumerate(zip(names,sources,roles),1):
            if preserve_covers and name=="01-cover":
                current_cover=next((page for page in current.get("pages",[]) if page.get("id")=="cover"),None)
                if not current_cover:raise ValueError(f"{slug}: --preserve-covers requires existing cover metadata")
                pages.append(current_cover);continue
            sp=sd/f"{name}.svg";wp=out/f"{name}.webp";sp.write_text(source,encoding="utf-8");raster(sp,wp);pages.append({"id":name[3:],"order":i,"role":role,"imagePath":f"/workbooks/{slug}/{name}.webp","thumbnailPath":f"/workbooks/{slug}/{name}.webp","sha256":sha(wp),"alt":f'{u["module"]} {i}쪽',"approved":True})
        generated={"id":slug,"slug":slug,"subject":"korean","title":f'초등 국어 한 장: {u["module"]}',"gradeBand":u["band"],"domain":u["domain"],"module":u["module"],"standardCodes":u["standards"],"levels":["read","explore","express"],"activities":{"textA":u["a"],"questionsA":u["qa"],"textB":u["b"],"questionsB":u["qb"],"focus":u["focus"],"produce":u["produce"],"model":u["model"]},"pages":pages,"pdf":{"path":f"/workbooks/{slug}/{slug}.pdf","pageCount":8,"sha256":"0"*64},"transcriptPath":f"/workbooks/{slug}/transcript.html","license":"CC-BY-NC-SA-4.0","author":"Taehyeong Lim","publishedAt":"2026-07-29","published":True}
        workbook={**generated,**current,"pages":pages,"pdf":generated["pdf"],"transcriptPath":current.get("transcriptPath",generated["transcriptPath"])}
        pdf(workbook);workbook["pdf"]["sha256"]=sha(PUBLIC/workbook["pdf"]["path"].lstrip("/"));(out/"transcript.html").write_text(transcript(u,workbook),encoding="utf-8");(CONTENT/"workbooks"/f"{slug}.json").write_text(json.dumps(workbook,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");cat["workbooks"].append(workbook);print(f"Rendered {slug}: 8 pages")
    cat["workbooks"].sort(key=lambda w:w["id"]);cp.write_text(json.dumps(cat,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return 0
if __name__=="__main__":raise SystemExit(main())
