# Printable wedding name cards

Edit `name-cards.txt`, keeping one guest name per line, then run:

```powershell
python generate_name_cards.py
```

This creates `output/pdf/wedding-name-cards-a4-sirivennela.pdf`. Each A4 sheet contains six
foldable tent cards with dotted cutting outlines and small centre fold marks. The
final three sheets contain six cards each labeled “Reserved”.

Optional arguments:

```powershell
python generate_name_cards.py --names another-list.txt --output output/pdf/cards.pdf --blank-pages 2
```
