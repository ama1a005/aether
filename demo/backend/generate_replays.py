"""Generate replay bundles by executing the same demo backend used by the API."""

from demo.backend.repository import load_cases
from demo.backend.service import generate_replay


def main() -> None:
    for case in load_cases():
        result = generate_replay(case.case_id)
        print(case.case_id, result["content_sha256"])


if __name__ == "__main__":
    main()
