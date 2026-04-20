## Context

현재 프로젝트에는 FastAPI 앱 진입점(`app/main.py`)과 기본 폴더 구조만 존재한다. `app/core/security.py`, `app/core/dependencies.py`, `app/db/models/`, `app/services/`, `app/schemas/`는 스캐폴딩 단계에서 빈 파일로 생성되었거나 아직 미존재 상태다. 인증 레이어가 전혀 없어 모든 엔드포인트가 비보호 상태이다.

## Goals / Non-Goals

**Goals:**
- Keycloak을 인증 서버로 사용하는 id/password 회원가입·로그인 흐름 구현
- SSO(Keycloak 페이지) 로그인 콜백 처리 및 DB users 자동 생성(upsert)
- access_token 만료 시 refresh_token으로 갱신
- JWT 검증 기반 `get_current_user` 의존성 — 다른 라우터가 재사용
- Swagger UI에서 BearerAuth로 보호된 엔드포인트 직접 테스트 가능

**Non-Goals:**
- 비밀번호 재설정·이메일 검증 (Keycloak이 담당)
- 소셜 로그인(Google, GitHub 등) 연동
- 토큰 블랙리스트·강제 로그아웃 서버사이드 세션
- Role/Permission 기반 인가 정책
- 관리자용 사용자 목록·계정 정지 기능

## Decisions

### 1. Keycloak Admin API 접근 방식: Service Account

Keycloak Admin REST API 호출 시 별도 admin 계정 대신 Client Service Account 토큰을 사용한다.
회원가입 흐름에서 백엔드가 Keycloak에 유저를 생성할 때 `POST /auth/admin/realms/{realm}/users`를 호출해야 하며, 이 API는 `manage-users` realm role이 필요하다.

**이유**: admin 계정 자격증명을 환경변수로 관리하면 범위가 너무 넓고, Client Credentials grant로 발급한 service account 토큰은 client_id·client_secret만으로 최소 권한 운영이 가능하다. `.env`에 KEYCLOAK_CLIENT_SECRET만 추가하면 되어 시크릿 범위를 최소화한다.

### 2. SSO 콜백 응답 방식: JSON 응답

`GET /api/v1/auth/callback?code=...`에서 token 교환 후 access_token·refresh_token을 JSON body로 반환한다. 쿼리 파라미터 리다이렉트 방식(Fragment hash 포함)은 사용하지 않는다.

**이유**: 쿼리 파라미터 방식은 토큰이 브라우저 히스토리·서버 로그에 노출될 위험이 있다. 프론트가 `/callback` URL을 직접 fetch하고 응답 JSON에서 토큰을 추출해 메모리에 보관하는 것이 보안상 우수하다. 이 결정은 프론트가 SPA 구조임을 전제한다.

### 3. JWT 검증: Keycloak 공개키 원격 fetch + 인메모리 캐싱

`app/core/security.py`에서 Keycloak의 JWKS endpoint(`/auth/realms/{realm}/protocol/openid-connect/certs`)를 호출해 공개키를 가져오고 `python-jose`로 서명 검증한다. 공개키는 프로세스 메모리에 캐싱하며 TTL은 600초(10분)로 설정한다.

**이유**: 매 요청마다 Keycloak에 공개키를 요청하면 불필요한 네트워크 왕복이 발생하고 Keycloak 장애 시 모든 요청이 실패한다. TTL 600초는 키 교체 주기(보통 수일~수주)보다 충분히 짧아 교체 감지에 실용적이다.

### 4. users 테이블 upsert 키: auth_id (Keycloak sub)

DB upsert 시 `auth_id`(JWT의 `sub` 클레임) 를 충돌 판별 키로 사용하고, `last_login_at`을 갱신한다. username·email은 upsert 시 Keycloak 토큰 클레임에서 추출해 동기화한다.

**이유**: `sub`는 Keycloak이 유저 생성 시 부여하는 불변 UUID로, id/password 가입과 SSO 가입 모두에서 동일한 유저를 식별하는 단일 키다. username·email은 Keycloak 관리자가 변경할 수 있으므로 매 로그인 시 동기화한다.

### 5. 에러 응답 구조: 단일 `detail` 필드

FastAPI 기본 `HTTPException`의 `detail` 필드를 사용한다. 별도 에러 코드 체계(error_code enum)는 이 기능 범위에서 도입하지 않는다.

**이유**: 현재 클라이언트(프론트 SPA)가 HTTP 상태 코드로 분기 처리가 충분하며, 에러 코드 체계 표준화는 서비스 전체 레벨의 결정이므로 이 기능 범위를 벗어난다. 추후 별도 변경 스펙으로 다룬다.

### 6. 레이어 분리: keycloak_service / user_service 분리

Keycloak HTTP 호출(`keycloak_service.py`)과 DB users 조작(`user_service.py`)을 별도 서비스로 분리한다. `auth.py` 라우터는 두 서비스를 조합하되 비즈니스 로직을 직접 포함하지 않는다.

**이유**: forbidden-patterns에 "라우터에 비즈니스 로직 직접 작성 금지" 규칙이 있다. 또한 keycloak_service는 httpx 비동기 HTTP 클라이언트를 사용하고 user_service는 AsyncSession을 사용하므로 책임 분리가 명확하다.

## Risks / Trade-offs

- **Keycloak 장애 시 로그인 불가**: Keycloak이 단일 장애점이다. 완화책: 502 응답으로 명확히 구분, 향후 헬스체크 엔드포인트와 연계.
- **공개키 캐시 stale**: TTL 내 키 교체 시 검증 실패가 발생할 수 있다. 완화책: 검증 실패 시 캐시 무효화 후 재시도 1회 로직 포함.
- **Service Account 시크릿 노출**: `KEYCLOAK_CLIENT_SECRET`이 유출되면 Admin API 접근 가능. 완화책: `.env` 커밋 금지 규칙(forbidden-patterns) 준수, 프로덕션은 vault/secret manager 사용 권장.
- **SSO 콜백 CSRF**: authorization code를 가로채 재사용하는 공격 가능성. 완화책: Keycloak의 state 파라미터 검증을 프론트 책임으로 명시, 백엔드는 code 단순 교환만 수행.
