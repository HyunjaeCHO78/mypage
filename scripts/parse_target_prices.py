"""목표주가/투자의견/날짜/증권사 파싱 초안 스크립트.

실제 파싱 로직은 데이터 소스 확정 이후 구현한다.
"""


def parse_target_prices(raw_record: dict) -> dict:
    """원본 레코드에서 핵심 필드를 추출하는 인터페이스 초안."""
    return {
        "최신목표가": raw_record.get("최신목표가", ""),
        "최신투자의견": raw_record.get("최신투자의견", ""),
        "최신리포트날짜": raw_record.get("최신리포트날짜", ""),
        "최근주요증권사": raw_record.get("최근주요증권사", ""),
    }


if __name__ == "__main__":
    print("parse_target_prices.py 초안: 실제 파싱 로직은 2차 구현 예정")
