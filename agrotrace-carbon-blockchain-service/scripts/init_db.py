from app.application.container import init_database


def main() -> None:
    init_database()
    print("Blockchain service database initialized.")


if __name__ == "__main__":
    main()
