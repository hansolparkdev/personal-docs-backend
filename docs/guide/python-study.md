# Python 학습 정리

## 목차

1. [개발 환경](#1-개발-환경)
2. [변수와 자료형](#2-변수와-자료형)
3. [조건문](#3-조건문)
4. [반복문](#4-반복문)
5. [함수](#5-함수)
6. [클래스](#6-클래스)
7. [예외처리](#7-예외처리)
8. [모듈과 import](#8-모듈과-import)
9. [데코레이터](#9-데코레이터)
10. [비동기 (async/await)](#10-비동기-asyncawait)
11. [FastAPI 기초](#11-fastapi-기초)

---

## 1. 개발 환경

### Python 버전 확인

```bash
python3 --version
```

### 가상환경 (Virtual Environment, venv)

프로젝트마다 독립된 Python 환경을 만드는 것. 라이브러리 버전 충돌을 방지합니다.

```bash
# 가상환경 생성 (처음 한 번만)
python3.11 -m venv .venv

# 가상환경 활성화 (터미널 열 때마다)
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate      # Windows

# 가상환경 비활성화
deactivate
```

- `(.venv)` 가 터미널 앞에 붙으면 활성화된 상태
- `-m` 은 module(모듈)의 약자. `python -m venv` = "venv 모듈을 실행해라"
- `source` = 현재 터미널에서 파일 실행 (`.` 으로도 가능)

### 패키지 관리 도구

| 도구 | 역할 | 특징 |
|------|------|------|
| `pip` | 라이브러리 설치 | Python 기본 내장 |
| `venv` | 가상환경 생성 | Python 기본 내장 |
| `uv` | pip + venv 통합 | 요즘 트렌드, 매우 빠름 |
| `poetry` | 의존성 관리 + 패키징 | npm과 비슷한 느낌 |

### requirements.txt

프로젝트에 필요한 라이브러리 목록 파일.

```bash
pip install -r requirements.txt  # 목록 전체 설치
pip install fastapi               # 개별 설치
```

`==` 으로 버전을 고정해서 팀원 모두 같은 버전을 씁니다:

```
fastapi==0.115.5
sqlalchemy==2.0.36
```

---

## 2. 변수와 자료형

### 변수

데이터를 담는 상자. `let`, `const`, `var` 없이 그냥 씁니다.

```python
name = "한솔"        # 문자열 (String)
age = 30             # 정수 (Integer)
height = 175.5       # 소수 (Float)
is_active = True     # 참/거짓 (Boolean)
value = None         # 없음 (JavaScript의 null)
```

### f-string (포맷 문자열)

변수를 문자열 안에 삽입. JavaScript 템플릿 리터럴과 같습니다.

```python
name = "한솔"
print(f"이름: {name}")  # 이름: 한솔

# JavaScript
# `이름: ${name}`
```

### 리스트 (List)

순서가 있는 데이터 모음. JavaScript 배열(Array)과 같습니다.

```python
fruits = ["사과", "바나나", "오렌지"]

fruits[0]      # 사과 (0부터 시작)
fruits[-1]     # 오렌지 (뒤에서 첫 번째)
fruits.append("포도")  # 추가
fruits.remove("바나나") # 삭제
len(fruits)    # 길이
```

### 딕셔너리 (Dictionary)

키-값 쌍으로 데이터를 담는 상자. JavaScript 객체(Object)와 같습니다.

```python
user = {"name": "한솔", "age": 30}

user["name"]   # 한솔 (.으로 접근 안 됨)
user["email"] = "test@test.com"  # 추가/수정
user.keys()    # 키 목록
user.values()  # 값 목록
user.items()   # 키-값 쌍 목록

# 타입이 섞인 경우
from typing import Any
data: dict[str, Any] = {"name": "한솔", "age": 30}
```

---

## 3. 조건문

```python
age = 30

if age >= 20:
    print("성인")
elif age >= 14:
    print("청소년")
else:
    print("어린이")
```

**핵심 규칙:**
- 조건 끝에 `:` 필수
- 들여쓰기(4칸)로 블록 구분 (중괄호 없음)

### 논리 연산자

JavaScript와 달리 영어로 씁니다:

```python
# JavaScript: && || !
# Python:     and or not

age >= 20 and name == "한솔"
age >= 20 or name == "한솔"
not is_active
```

---

## 4. 반복문

### for — 정해진 횟수만큼 반복

```python
# 리스트 순회
fruits = ["사과", "바나나", "오렌지"]
for fruit in fruits:
    print(fruit)

# range() — 숫자 반복
for i in range(5):      # 0, 1, 2, 3, 4
    print(i)

for i in range(1, 6):   # 1, 2, 3, 4, 5
    print(i)

# enumerate() — 인덱스 + 값
for i, fruit in enumerate(fruits):
    print(i, fruit)  # 0 사과, 1 바나나...

# 딕셔너리 순회
user = {"name": "한솔", "age": 30}
for key, value in user.items():
    print(f"{key}: {value}")
```

### while — 조건이 참인 동안 반복

```python
count = 0
while count < 3:
    print(count)
    count += 1  # 0, 1, 2
```

### break / continue

```python
# break — 반복 중단
for i in range(10):
    if i == 5:
        break
    print(i)  # 0, 1, 2, 3, 4

# continue — 이번 회차 건너뜀
for i in range(5):
    if i == 2:
        continue
    print(i)  # 0, 1, 3, 4
```

---

## 5. 함수

반복되는 코드를 묶어서 이름 붙인 것.

```python
# 기본 함수
def greet(name):
    print(f"안녕하세요 {name}님")

greet("한솔")

# return — 값 반환
def add(a, b):
    return a + b

result = add(3, 5)  # 8

# 기본값 (default)
def greet(name, message="안녕하세요"):
    print(f"{message} {name}님")

greet("한솔")              # 안녕하세요 한솔님
greet("한솔", "반갑습니다") # 반갑습니다 한솔님

# 여러 값 반환
def get_user():
    return "한솔", 30

name, age = get_user()
```

### 타입 힌트 (Type Hint)

함수 인자와 반환값의 타입을 명시합니다. FastAPI에서 핵심입니다.

```python
def add(a: int, b: int) -> int:
    return a + b

# 자주 쓰는 타입
def func(
    name: str,
    age: int,
    tags: list[str],
    data: dict[str, Any],
    email: str | None,    # str 또는 None
) -> str:
    return name
```

- 강제가 아님 (런타임에서 검증 안 함)
- FastAPI는 타입 힌트로 **자동 검증** 합니다

---

## 6. 클래스

데이터와 기능을 하나로 묶은 설계도.

```python
class User:
    def __init__(self, name, age):  # 생성자 (Constructor)
        self.name = name            # self = 자기 자신
        self.age = age
    
    def greet(self):
        print(f"안녕하세요 {self.name}입니다")
    
    def is_adult(self):
        return self.age >= 20

user = User("한솔", 30)
user.greet()
print(user.name)
```

- `__init__` = 생성자. 객체 만들 때 자동 실행 (JavaScript `constructor` 와 같음)
- `self` = 자기 자신 (JavaScript `this` 와 같지만 항상 고정)

### 상속 (Inheritance)

부모 클래스의 기능을 물려받습니다.

```python
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        print("...")

class Dog(Animal):  # Animal 상속
    def speak(self):  # 부모 메서드 덮어씀 (오버라이딩)
        print(f"{self.name}: 멍멍")

dog = Dog("바둑이")
dog.speak()  # 바둑이: 멍멍
```

### super() — 부모 메서드 호출

추가 인자가 필요할 때만 `__init__` 을 직접 정의하고 `super()` 로 부모를 호출합니다.

```python
class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)  # 부모 __init__ 실행
        self.breed = breed      # 추가 속성

dog = Dog("바둑이", "진돗개")
```

**추가 인자 없으면 `__init__` 안 써도 됩니다. 부모 것을 그대로 씁니다.**

### 언더스코어 (Underscore) 규칙

| 형태 | 의미 | 예시 |
|------|------|------|
| `__name__` | Python 예약 (던더, Dunder = Double Underscore) | `__init__`, `__str__` |
| `_name` | 내부용 관례 (강제 아님) | `_password` |
| `__name` | 진짜 외부 접근 차단 | `__secret` |

- **던더(Dunder)** = Double Underscore의 줄임말
- `__init__`, `__str__`, `__tablename__` 등은 Python이 특별하게 처리하는 예약된 이름

---

## 7. 예외처리

에러가 발생해도 프로그램이 죽지 않게 처리합니다.

```python
try:
    number = int("abc")   # 에러 발생
except ValueError as e:   # 특정 에러 처리
    print(f"에러: {e}")
except Exception as e:    # 모든 에러 처리 (마지막에)
    print(f"기타 에러: {e}")
finally:
    print("항상 실행")    # 에러 있든 없든 실행
```

**규칙:** 구체적인 에러 먼저, 넓은 에러 나중에

### raise — 에러 발생 (JavaScript `throw` 와 같음)

```python
def check_age(age):
    if age < 0:
        raise ValueError("나이는 0 이상이어야 합니다")

try:
    check_age(-1)
except ValueError as e:
    print(e)
```

### 커스텀 예외

```python
class UnsupportedFormatError(Exception):
    pass

raise UnsupportedFormatError("지원하지 않는 포맷입니다")
```

### 에러 전파

`raise` 는 **콜스택 위로** 전달됩니다. 누군가 `except` 로 잡을 때까지 올라갑니다.

```python
def c():
    raise ValueError("에러!")  # 발생

def b():
    c()  # c에서 올라옴 → 잡지 않으면 위로 전달

def a():
    b()  # b에서 올라옴

try:
    a()
except ValueError as e:
    print(e)  # 여기서 잡힘
```

---

## 8. 모듈과 import

Python 파일 하나 = 모듈 하나

```python
# 모듈 전체 import
import calculator
calculator.add(3, 5)

# 특정 함수만 import
from calculator import add
add(3, 5)

# 별칭 (alias)
import calculator as calc
from calculator import add as plus
```

### 패키지 (Package)

폴더 단위의 모듈 모음. `__init__.py` 파일이 있으면 패키지로 인식합니다.

```
app/
├── __init__.py    ← 패키지 표시 (Python 3.3+ 에서는 없어도 됨, 취향 차이)
└── services/
    ├── __init__.py
    └── user_service.py
```

```python
from app.services.user_service import get_user
```

- `__init__.py` = JavaScript `index.ts` 와 같은 역할
- 안에 공통 import를 모아두면 경로를 짧게 쓸 수 있음

---

## 9. 데코레이터

함수에 기능을 추가하는 문법. `@` 기호를 씁니다.

```python
def log(func):              # 데코레이터 함수
    def wrapper():
        print("실행 전")
        result = func()     # 원래 함수 실행
        print("실행 후")
        return result
    return wrapper

@log                        # = hello = log(hello)
def hello():
    print("안녕하세요")

hello()
# 실행 전
# 안녕하세요
# 실행 후
```

### @wraps — 함수 이름 유지

```python
from functools import wraps

def log(func):
    @wraps(func)   # 원래 함수 이름 유지
    def wrapper():
        return func()
    return wrapper
```

- `@wraps` 없으면 `hello.__name__` 이 `wrapper` 로 바뀜
- `@wraps` 있으면 `hello.__name__` 이 `hello` 유지

### 자주 쓰는 데코레이터

```python
# FastAPI 라우터
@router.get("/users")
@router.post("/users")
@router.delete("/users/{id}")

# 클래스
@staticmethod   # self 없는 메서드, 인스턴스 없이 호출 가능
@classmethod    # cls(클래스 자체)를 받는 메서드
@property       # 메서드를 변수처럼 접근

class User:
    @staticmethod
    def validate(email):
        return "@" in email

    @property
    def full_name(self):
        return f"{self.first} {self.last}"

User.validate("test@test.com")  # 인스턴스 없이 호출
user.full_name                  # () 없이 변수처럼 접근
```

---

## 10. 비동기 (async/await)

### 동기 vs 비동기

**동기 (Synchronous):** 한 번에 하나씩 순서대로 처리. 기다리는 동안 아무것도 못 함.

**비동기 (Asynchronous):** 기다리는 동안 다른 일 처리. 이벤트루프가 관리.

### 이벤트루프 (Event Loop)

JavaScript 이벤트루프와 완전히 같은 개념입니다.

```
콜스택 (Call Stack)  — 지금 실행 중인 함수들의 쌓임 (LIFO)
이벤트루프           — 콜스택이 비면 대기 목록에서 꺼내서 실행
대기 목록            — await 중인 작업들
```

```
요청 들어옴 → 콜스택에 쌓임
await 만남 → 외부(DB/API)에 요청 보내고 콜스택에서 빠짐
콜스택 비워짐 → 다음 요청 처리 가능
외부 응답 옴 → 대기 목록에 넣음
콜스택 비면 → 대기 목록에서 꺼내서 재개
```

### async / await

```python
# async def — 비동기 함수 (코루틴, Coroutine) 선언
async def get_user():
    # await — 여기서 콜스택 빠짐, 완료되면 재개
    result = await db.execute(select(User))
    return result
```

- `async def` 로 만든 함수 = **코루틴(Coroutine)**
- `await` 없이 호출하면 코루틴 객체만 반환됨 (실행 안 됨)
- `await` 는 `async def` 안에서만 사용 가능

### asyncio

Python 비동기 처리를 위한 내장 모듈

```python
import asyncio

# 여러 비동기 작업 동시 실행
async def main():
    await asyncio.gather(
        task1(),  # 동시에
        task2(),  # 실행
        task3(),  # 됨
    )

asyncio.run(main())  # 이벤트루프 시작
```

### yield — 제너레이터 (Generator)

값을 하나씩 순서대로 내보냅니다. SSE 스트리밍에서 핵심입니다.

```python
def numbers():
    yield 1
    yield 2
    yield 3

for n in numbers():
    print(n)  # 1, 2, 3

# 비동기 제너레이터 — SSE 스트리밍
async def stream():
    async for token in llm.astream(...):
        yield f"event: token\ndata: {token}\n\n"
    yield "event: done\ndata: {}\n\n"
```

### FastAPI에서 비동기를 쓰는 이유

Python에는 **GIL(Global Interpreter Lock)** 이 있어서 멀티스레드가 진짜 병렬처리가 안 됩니다. API 서버는 DB 조회, 외부 API 호출 같은 **I/O(입출력) 대기 작업**이 대부분이라 비동기가 훨씬 효율적입니다.

| 방식 | 동시 처리 | 특징 |
|------|-----------|------|
| 동기 + 멀티스레드 (Flask, Django) | 스레드 수만큼 | GIL로 진짜 병렬 안 됨 |
| 비동기 이벤트루프 (FastAPI, Node.js) | 매우 많음 | 메모리 효율적 |
| 고루틴 (Go) | 수백만개 | 경량 스레드 (2KB) |

### 스레드 풀 (Thread Pool)

동기 프레임워크에서 성능을 위해 미리 스레드를 만들어두고 재사용하는 방식.

```
스레드 풀 20개:
요청 1~20 → 각각 스레드 할당 → 동시 처리
요청 21   → 스레드 반납될 때까지 대기
```

---

## 11. FastAPI 기초

### 기본 구조

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
async def hello():
    return {"message": "안녕하세요"}
```

서버 실행:
```bash
uvicorn app.main:app --reload
# uvicorn — ASGI(Asynchronous Server Gateway Interface) 서버
# app.main — app 폴더의 main.py
# :app — main.py 안의 app 변수
# --reload — 코드 변경 시 자동 재시작
```

### APIRouter — 라우터 분리

```python
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("")           # GET /users
@router.get("/{user_id}") # GET /users/123 (Path Parameter)
@router.post("")          # POST /users
@router.delete("/{id}")   # DELETE /users/123
```

**prefix 조합:**
```
app.include_router(router)      → 없음
  router.include_router(users)  → /api/v1
    users.router                → /users

최종: /api/v1/users
```

### Path Parameter vs Query Parameter

```python
# Path Parameter — URL 경로에 포함
@router.get("/{user_id}")
async def get_user(user_id: int):
    pass
# /users/123

# Query Parameter — URL 뒤에 ?로 붙음
@router.get("")
async def list_users(page: int = 1, size: int = 10):
    pass
# /users?page=2&size=20
```

### Pydantic 스키마 — 요청/응답 형식

```python
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    # body.username, body.password 자동 검증됨
    return TokenResponse(access_token="...", expires_in=300)
```

### HTTPException — HTTP 에러 반환

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="유저 없음")
raise HTTPException(status_code=401, detail="인증 필요")
raise HTTPException(status_code=409, detail="이미 존재함")
```

### Depends — 의존성 주입 (Dependency Injection)

중복 코드를 함수로 만들어서 재사용합니다.

```python
from fastapi import Depends

# 한 번만 작성
async def get_current_user(...) -> User:
    # 토큰 검증
    # DB에서 유저 조회
    return user

# 모든 보호된 API에서 재사용
@router.get("/files")
async def list_files(
    current_user: User = Depends(get_current_user)  # 자동 실행
):
    return await file_service.list_files(current_user.auth_id)
```

- `Depends` = "이 함수를 먼저 실행하고 결과를 넣어줘"
- 같은 `Depends` 는 한 요청에서 한 번만 실행됨
- 중첩 가능 (`get_current_user` 안에도 `Depends` 사용 가능)

---

## 용어 정리

| 용어 | 풀이 | 설명 |
|------|------|------|
| venv | Virtual Environment | 가상환경 |
| pip | Pip Installs Packages | Python 패키지 설치 도구 |
| GIL | Global Interpreter Lock | Python 멀티스레드 제한 |
| ASGI | Asynchronous Server Gateway Interface | 비동기 웹 서버 인터페이스 |
| ORM | Object Relational Mapping | DB 테이블을 Python 클래스로 다루는 방식 |
| I/O | Input/Output | 입출력 (DB 조회, 파일 읽기, API 호출 등) |
| SSE | Server-Sent Events | 서버에서 클라이언트로 실시간 데이터 전송 |
| LIFO | Last In First Out | 나중에 들어온 것이 먼저 나감 (콜스택) |
| FIFO | First In First Out | 먼저 들어온 것이 먼저 나감 (이벤트 큐) |
| Dunder | Double Underscore | `__init__` 같이 양쪽에 `__` 가 붙은 것 |
| Coroutine | 코루틴 | `async def` 로 만든 비동기 함수 |
| Generator | 제너레이터 | `yield` 로 값을 하나씩 반환하는 함수 |
| DI | Dependency Injection | 의존성 주입. FastAPI의 `Depends` |
