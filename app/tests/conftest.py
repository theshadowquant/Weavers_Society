import os
try:
    import pytest

    @pytest.fixture(scope="session", autouse=True)
    def setup_test_db():
        # Initialize isolated test database
        init_db(force=True)
        yield
        # Clean up test database after test suite completes
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass
except ImportError:
    pass
