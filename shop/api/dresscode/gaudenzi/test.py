# logger_test.py - 단계별 로거 문제 진단

import os
import sys
import logging
from pathlib import Path

# Django 환경 설정
sys.path.insert(0, r'C:\Users\USER\myproject\mallapi')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")

import django
django.setup()

def test_step_by_step():
    print("🧪 단계별 로거 테스트 시작")
    print("=" * 50)
    
    # 1단계: 기본 디렉토리 확인
    print("\n1️⃣ 디렉토리 테스트")
    print("-" * 20)
    current_dir = Path.cwd()
    print(f"현재 디렉토리: {current_dir}")
    
    test_log_dir = current_dir / "test_logs"
    test_log_dir.mkdir(exist_ok=True)
    print(f"테스트 로그 디렉토리: {test_log_dir}")
    print(f"디렉토리 존재: {test_log_dir.exists()}")
    print(f"쓰기 권한: {os.access(test_log_dir, os.W_OK)}")
    
    # 2단계: 기본 파일 생성 테스트
    print("\n2️⃣ 파일 생성 테스트")
    print("-" * 20)
    test_file = test_log_dir / "basic_test.txt"
    try:
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("테스트 파일")
        print(f"✅ 파일 생성 성공: {test_file}")
        print(f"파일 크기: {test_file.stat().st_size} bytes")
    except Exception as e:
        print(f"❌ 파일 생성 실패: {e}")
        return
    
    # 3단계: 기본 로깅 테스트
    print("\n3️⃣ 기본 로깅 테스트")
    print("-" * 20)
    log_file = test_log_dir / "basic_logging.log"
    
    # 새로운 로거 생성
    test_logger = logging.getLogger("basic_test")
    test_logger.handlers.clear()  # 기존 핸들러 제거
    test_logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러 생성
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        file_handler.setFormatter(formatter)
        
        test_logger.addHandler(file_handler)
        
        print(f"핸들러 추가 완료: {len(test_logger.handlers)}개")
        
        # 테스트 로그 작성
        test_logger.debug("🔍 DEBUG 메시지")
        test_logger.info("📝 INFO 메시지")  
        test_logger.warning("⚠️ WARNING 메시지")
        test_logger.error("❌ ERROR 메시지")
        
        # 핸들러 강제 플러시
        file_handler.flush()
        
        print(f"로그 파일 존재: {log_file.exists()}")
        if log_file.exists():
            size = log_file.stat().st_size
            print(f"로그 파일 크기: {size} bytes")
            
            if size > 0:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print("📖 로그 파일 내용:")
                    print(content)
            else:
                print("❌ 로그 파일이 비어있음")
        
        # 핸들러 정리
        file_handler.close()
        test_logger.removeHandler(file_handler)
        
    except Exception as e:
        print(f"❌ 기본 로깅 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4단계: product_logger 테스트
    print("\n4️⃣ product_logger 테스트")
    print("-" * 20)
    try:
        from utils.product_logger import get_product_logger
        
        print("product_logger import 성공")
        
        # 기존 로거 핸들러 확인
        existing_logger = logging.getLogger("product_logger_IT-G-03")
        print(f"기존 로거 핸들러 수: {len(existing_logger.handlers)}")
        
        # 새 로거 생성
        prod_logger = get_product_logger("IT-G-03")
        print(f"새 로거 핸들러 수: {len(prod_logger.handlers)}")
        
        # 테스트 로그 작성
        prod_logger.info("🧪 product_logger 테스트")
        
        # 핸들러 정보 출력
        for i, handler in enumerate(prod_logger.handlers):
            print(f"핸들러 {i}: {type(handler).__name__}")
            if hasattr(handler, 'stream'):
                print(f"  스트림: {handler.stream}")
            if hasattr(handler, 'baseFilename'):
                print(f"  파일: {handler.baseFilename}")
                file_path = Path(handler.baseFilename)
                print(f"  파일 존재: {file_path.exists()}")
                if file_path.exists():
                    print(f"  파일 크기: {file_path.stat().st_size} bytes")
        
    except Exception as e:
        print(f"❌ product_logger 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_step_by_step()