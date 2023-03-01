# Late Days Script

This is a script to generate each student's remaining late days for the Data Structures in Java course at Columbia (COMS W3134).

## Getting the necessary CSV files

1. Courseworks: Grades -> Action -> Export
2. Gradescope (Written): Dashboard -> Assignment -> Review Grades -> Download Grades -> Download CSV
3. Codio (Programming): Courses -> 3 dots next to Assignment -> Download CSV

Ensure each of these files is in the same directory as ```latedays.py```.

## Usage

Download the necessary CSVs and update their filenames in ```latedays.py```. Then, run:

```bash
pip install -r requirements.txt
python3 latedays.py
```

## Credits

Whitney Deng wrote a script for this task last year when the class still tracked late hours rather than days. This script heavily draws from hers!