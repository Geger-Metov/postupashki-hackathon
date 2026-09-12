from src.db import engine
from src.models import Base


def create_all():
    Base.metadata.create_all(engine)
    print("Таблицы созданы:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")


if __name__ == "__main__":
    create_all()