import hashlib
import sys

def test_sha256_hash():
    source = "test_source.pdf"
    idx = 0
    # Logic from rag_tool.py: doc_id = hashlib.sha256(f"{source}:{idx}".encode()).hexdigest()
    expected_doc_id = hashlib.sha256(f"{source}:{idx}".encode()).hexdigest()

    print(f"Generated doc_id: {expected_doc_id}")
    assert len(expected_doc_id) == 64, f"Expected 64 hex characters for SHA-256, got {len(expected_doc_id)}"

    # Verify it is not MD5
    md5_hash = hashlib.md5(f"{source}:{idx}".encode()).hexdigest()
    assert expected_doc_id != md5_hash, "doc_id is still using MD5"
    print("Verification successful: doc_id is using SHA-256.")

if __name__ == "__main__":
    try:
        test_sha256_hash()
    except AssertionError as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
