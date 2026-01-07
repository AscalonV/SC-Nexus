import multiprocessing
from src.app import run_app

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_app()
