# Winix HA Integration - Development Notes

## 프로젝트 목표

iprak/winix 기반의 HA custom component를 Winix사의 공기청정기 외에 창문형 에어컨과 제습기도
지원하도록 확장한다.

- **공기청정기 (Air Purifier)**: 기존 코드 유지
- **제습기 (Dehumidifier)**: 완전 지원 구현
- **창문형 에어컨 (Air Conditioner)**: 껍데기만 (패킷 미확인)

---

## 참고 자료

### 1. hfern/winix dev 브랜치 (CLI 툴)
URL: https://github.com/hfern/winix/compare/master...1saac-k:winixctl:dev

6개 커밋으로 구성:
1. `refactor: use DEFAULT_CONFIG_PATH in main` - 사소한 리팩토링
2. `refactor: change WinixDevice as base class for all product group` - WinixDevice를 기반 클래스로
3. `feature: add dehumidifier and airconditioner device type` - 제습기/에어컨 지원 추가 (DWXE210 모델 테스트됨)
4. `doc: not limited to airpurifiers` - 문서 업데이트
5. `feature: add brightness, child_lock control for airpurifier` - 공기청정기에 brightness/child_lock
6. `feature: add humidity-hist command for dehumidifier` - 습도 이력 조회

핵심 내용:
- 기본 클래스: `WinixDevice` (control + get_state)
- 제습기 API 키: D02(power), D03(mode), D04(airflow), D05(humidity), D08(child_lock), D10(current_humidity), D13(uv), D15(timer)
- 제습기 모드: auto(01), manual(02), laundry_dry(03), shoes_dry(04), silent(05), continuous(06)
- 제습기 airflow: high(01), low(02), turbo(03)

### 2. kjy8850/winix (HA 통합, 제습기만 지원)
URL: https://github.com/kjy8850/winix

- iprak/winix 포크, 공기청정기 기능 제거하고 제습기만 추가
- `WinixDehumidifier` entity: HumidifierEntity 기반
- 습도 범위: 35~70%, 5% 단위
- 제습기 모드: auto, manual, laundry_dry, shoes_dry, silent, continuous (한국어 레이블)
- 제습기 서비스: set_humidity, set_mode, set_fan_speed, set_timer, set_child_lock, set_uv_sterilization

---

## 제습기 API 매핑

### category_keys (D 시리즈)
```python
ATTR_POWER:           "D02"
ATTR_MODE:            "D03"
ATTR_AIRFLOW:         "D04"
ATTR_TARGET_HUMIDITY: "D05"
ATTR_CHILD_LOCK:      "D08"
ATTR_CURRENT_HUMIDITY:"D10"
ATTR_WATER_BUCKET:    "D11"
ATTR_UV_SANITIZE:     "D13"
ATTR_TIMER:           "D15"
```

### state_keys
```python
ATTR_POWER: {off: "0", on: "1", off-dry: "2"}
ATTR_MODE:  {auto: "01", manual: "02", clothes: "03", shoes: "04", quiet: "05", continuous: "06"}
ATTR_AIRFLOW: {high: "01", low: "02", turbo: "03"}
ATTR_CHILD_LOCK: {off: "0", on: "1"}
ATTR_WATER_BUCKET: {off: "0", on: "1"}  # on = full or detached
ATTR_UV_SANITIZE: {off: "0", on: "1"}
```

### 습도 범위
- 최소: 35%, 최대: 70%, 단위: 5%
- target_humidity는 정수 값으로 직접 전달 (state_keys 없음)

---

## 파일 구조

```
custom_components/winix/
├── __init__.py          # 플랫폼 등록 (fan, sensor, select, switch + 추가 예정: binary_sensor, humidifier)
├── binary_sensor.py     # 물통 가득 참 binary sensor (NEW)
├── const.py             # 상수 정의
├── config_flow.py       # HA 설정 UI
├── device_wrapper.py    # 디바이스 상태 관리 래퍼
├── driver.py            # API 통신 드라이버
├── fan.py               # 공기청정기 FAN entity
├── helpers.py           # 로그인, 디바이스 목록 조회 등 유틸리티
├── humidifier.py        # 제습기 Humidifier entity (NEW)
├── manager.py           # WinixManager (DataUpdateCoordinator), WinixEntity 기반 클래스
├── select.py            # 밝기 조절 등 select entity
├── sensor.py            # 공기질 센서
├── services.yaml        # 서비스 정의
├── strings.json         # 문자열
├── switch.py            # PlasmaWave, child_lock, UV sanitize 스위치
└── translations/en.json
```

---

## 주요 TODO 사항 (kyet: 주석)

### const.py
- [x] `ATTR_BRIGHTNESS_LEVEL`, `ATTR_CHILD_LOCK` → const.py로 이동
- [x] 제습기 관련 상수 추가

### driver.py
- [x] WinixDevice 기반 클래스 + AirPurifierDevice, DehumidifierDevice, AirConditionerDevice 분리
- [ ] `from .const import *` → 명시적 import로 교체

### device_wrapper.py
- [x] `product_group` 필드 추가
- [x] product_group으로 드라이버 선택
- [ ] `else  # TODO:` 구문 오류 수정 (`else:`)
- [ ] `self._features.uv_sanitize` → `supports_uv_sanitize` 오타 수정
- [ ] `async_child_lock_off` 이름 중복 → UV sanitize off는 `async_uv_sanitize_off`로 이름 변경
- [ ] `elif device_stub.model.lower().startswith("dxw*-21*")` - 와일드카드 미지원
- [ ] AirPurifierDevice, DehumidifierDevice, AirConditionerDevice import 추가

### binary_sensor.py
- [ ] 오타 수정: `WininxBinarySensorEntityDescription` → `WinixBinarySensorEntityDescription`
- [ ] 오타 수정: `entity_description: WininxSensorEntityDescription` → 올바른 타입
- [ ] `BINARY_SENSOR_WATER_BUCKET` import 누락 → const에서 import

### humidifier.py
- [ ] 전체 재작성 필요 (fan.py에서 복사 후 미수정)
- [ ] WinixPurifier → WinixDehumidifier
- [ ] 팬 관련 import/코드 → 제습기용으로 교체
- [ ] 습도 설정, 모드 설정, 팬속도 설정 구현

### __init__.py
- [ ] `SUPPORTED_PLATFORMS`에 `Platform.BINARY_SENSOR`, `Platform.HUMIDIFIER` 추가

### helpers.py
- [ ] 물통 알람 기능 추가 여부 검토 (kyet 주석)

### select.py
- [ ] 제습기용 airflow select 추가
- [ ] timer 구현 방식 결정 (select vs number)

---

## 구현 우선순위

1. 커밋 분할 (aba78765 → 작은 단위)
2. binary_sensor.py 버그 수정
3. device_wrapper.py 버그 수정
4. __init__.py 플랫폼 등록
5. humidifier.py 완성
6. 제습기 device_wrapper 메서드 추가 (set_mode, set_humidity, set_fan_speed 등)
7. select.py 제습기 airflow 추가
8. timer 구현

---

## 커밋 가이드라인

### Author 설정
```
Name: Kwangjin Ko
Email: kyet@me.com
```

### Signed-off-by
모든 커밋에 `Signed-off-by: Kwangjin Ko <kyet@me.com>` 추가

### 커밋 형식
```
<type>(<scope>): <짧은 설명>

[본문 - 선택사항]

Signed-off-by: Kwangjin Ko <kyet@me.com>
```

- type: feat, fix, refactor, chore, docs
- scope: 파일명 또는 기능명 (생략 가능)
- **Claude Code 링크 절대 포함 금지**
- **Co-authored-by 절대 포함 금지**

### Git 명령어 예시
```bash
git commit --author="Kwangjin Ko <kyet@me.com>" -m "$(cat <<'EOF'
feat(humidifier): add WinixDehumidifier entity

Signed-off-by: Kwangjin Ko <kyet@me.com>
EOF
)"
```

---

## 커밋 분할 계획 (aba78765 → 10개 커밋)

| # | 커밋 | 파일 |
|---|------|------|
| 1 | `chore(manager): remove stale category_keys comment` | manager.py |
| 2 | `refactor(const,driver): move ATTR_BRIGHTNESS_LEVEL, ATTR_CHILD_LOCK to const` | const.py, driver.py, device_wrapper.py |
| 3 | `feat(const): add dehumidifier constants and mode definitions` | const.py |
| 4 | `refactor(driver): extract WinixDevice base class with product-type subclasses` | driver.py |
| 5 | `feat(helpers): pass product_group from API response to device stub` | helpers.py |
| 6 | `feat(device_wrapper): add product_group field and product-type driver selection` | device_wrapper.py |
| 7 | `feat(device_wrapper,switch): add UV sanitize support` | device_wrapper.py, switch.py |
| 8 | `feat(device_wrapper): track water bucket state` | device_wrapper.py |
| 9 | `feat(binary_sensor): add water bucket binary sensor` | binary_sensor.py |
| 10 | `feat(humidifier,__init__): add WinixDehumidifier entity skeleton` | humidifier.py, __init__.py |
