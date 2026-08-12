try:
    from .parse_docx import run as extract
    from .merge_places import merge
    from .normalize_csv import normalize
    from .audit import audit
except ImportError:
    from parse_docx import run as extract
    from merge_places import merge
    from normalize_csv import normalize
    from audit import audit

def main():

    print("STEP 1: extract docx")
    extract()

    print("STEP 2: merge places")
    merge()

    print("STEP 3: normalize csv")
    normalize()

    print("STEP 4: audit")
    audit()

    print("DONE")

if __name__ == "__main__":
    main()
