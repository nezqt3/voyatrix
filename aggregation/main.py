from parse_docx import run as extract
from merge_places import merge

def main():

    print("STEP 1: extract docx")
    extract()

    print("STEP 2: merge places")
    merge()

    print("DONE")

if __name__ == "__main__":
    main()