# Piggdekk Support Dashboard 🛞

Streamlit dashboard that visualises Norwegian municipalities which offer financial support
for switching from studded winter tires (**piggdekk**) to non-studded winter tires
(**piggfrie vinterdekk**).

## Features

- Map of municipalities with piggdekk support.
- Filter by county and by support status.
- Table with:
  - support amount per tire
  - max number of tires
  - max total NOK
  - period of the scheme
  - basic contact info (service name, phone, website)
  - link to official info page

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py
