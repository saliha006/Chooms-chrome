def pytest_configure(config):
    config.addinivalue_line("markers", "slow: end-to-end model training (minutes); skip with -m 'not slow'")
