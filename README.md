# Shenbao Newspaper Search

A Python-based GUI application for searching through digitized Shenbao newspaper text files. This tool allows users to search for keywords within text files stored in the `shenbao-txt/txt` directory, with support for regular expressions, whole word matching, and vague searches. Results are displayed with context, page numbers, and highlighted matches, sorted by year in ascending or descending order.

## Features
- **Keyword Search**: Supports three modes:
  - **Regex**: Use regular expressions for precise pattern matching.
  - **Whole Word**: Match exact words only.
  - **Vague**: Flexible matching with wildcards between characters.
- **Year Filtering**: Filter search results by a range of years extracted from filenames.
- **Sorting**: Toggle between ascending and descending year order.
- **Result Display**: Shows filename, page number, matched keyword, and surrounding context with highlighting.

## Prerequisites
Before running the project, you need to:
1. Install Python 3.6 or higher.
2. Clone the Shenbao text repository to obtain the necessary `.txt` files.

### Cloning the Repository
Run the following command to download the Shenbao text files:
```bash
git clone https://github.com/moss-on-stone/shenbao-txt.git
```

### Run the client
Start the client via:
```bash
python SearchClient.py
```
