#!/usr/bin/env python3
"""
Translate Chinese content in Altium Designer SchLib file to English.
Uses same-size in-place writes via olefile.write_stream().
Only translates fields where the encoded translation fits within original byte length.
Preserves all OLE structure and binary content exactly.
"""
import olefile
import os
import re
import shutil
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHLIB_FILES = sorted(glob.glob(os.path.join(SCRIPT_DIR, "*.SchLib")))

# ─── Translation Dictionary ──────────────────────────────────────

TRANSLATIONS = {
    '贴片电阻': 'SMD Resistor',
    '贴片电容': 'SMD Capacitor',
    '贴片电感': 'SMD Inductor',
    '贴片磁珠': 'SMD Ferrite Bead',
    '贴片无源晶体': 'SMD Passive Crystal',
    '功率电感': 'Power Inductor',
    '层叠电感': 'Multilayer Inductor',
    '发光二极管': 'LED',
    '肖特基二极管': 'Schottky Diode',
    '压敏电阻': 'Varistor',
    '天线': 'Antenna',
    '倒F': 'Inverted-F',
    '三色': '',
    '白光': '',
    'PCB定位点': 'PCB Fiducial Mark',
    '测试点': 'Test Point',
    'PCB制造和工艺说明': 'PCB Fabrication and Process Notes',
    'PCB 层叠信息': 'PCB Layer Stackup Information',
    'PCB Gerber图纸模板': 'PCB Gerber Drawing Template',
    'RF电阻': 'RF Resistor',
    '纽扣电池3V': 'Coin Cell Battery 3V',
    '双向TVS': 'Bidirectional TVS',
    'ESD 双向TVS': 'ESD Bidirectional TVS',
    '未承认': 'Unapproved',
    '标准款': 'Standard',
    '标准版': 'Standard',
    '电池触点弹片，镀金，正极': 'Battery Contact Spring, Gold-Plated, Positive (+)',
    '电池触点弹片，镀金，负极': 'Battery Contact Spring, Gold-Plated, Negative (-)',
}

PATTERNS = [
    (r'20230825泰凌微根据我们的需求调整的管脚布局',
     'Telink pin layout adjusted per our requirements (20230825)'),
    (r'(\d+\.?\d*)寸_(\w+) ESL板框,标准版',
     lambda m: f'{m.group(1)}" ESL Board Outline ({m.group(2)}), Standard'),
    (r'(\d+\.?\d*)寸ESL板框,标准版',
     lambda m: f'{m.group(1)}" ESL Board Outline, Standard'),
    (r'(\d+\.?\d*)寸_(\w+) ESL板框,标准款',
     lambda m: f'{m.group(1)}" ESL Board Outline ({m.group(2)}), Standard'),
    (r'(\d+\.?\d*)寸ESL板框,标准款',
     lambda m: f'{m.group(1)}" ESL Board Outline, Standard'),
    (r'(\d+\.?\d*)寸_(\w+) ESL板框',
     lambda m: f'{m.group(1)}" ESL Board Outline ({m.group(2)})'),
    (r'(\d+\.?\d*)寸ESL板框',
     lambda m: f'{m.group(1)}" ESL Board Outline'),
    (r'(\d+\.?\d*)G PCB天线，倒F，VG(\d+\.?\d*)寸标准款专用',
     lambda m: f'{m.group(1)}G PCB Inverted-F Antenna, Standard VG{m.group(2)}"'),
    (r'(\d+\.?\d*)G PCB天线，倒F，VG(\d+\.?\d*)寸超薄款专用',
     lambda m: f'{m.group(1)}G PCB Inverted-F Antenna, Ultra-Thin VG{m.group(2)}"'),
    (r'(\d+\.?\d*)G PCB天线，倒F，(\d+\.?\d*)寸专用',
     lambda m: f'{m.group(1)}G PCB Inverted-F Antenna, for {m.group(2)}"'),
    (r'(\d+\.?\d*)G PCB天线，倒F，(.*)',
     lambda m: f'{m.group(1)}G PCB Inverted-F Antenna, {_translate_desc(m.group(2))}'),
    (r'NFC PCB天线，(\d+)匝，VG(\d+\.?\d*)寸标准款专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, Standard VG{m.group(2)}"'),
    (r'NFC PCB天线，(\d+)匝，VG(\d+\.?\d*)寸超薄款专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, Ultra-Thin VG{m.group(2)}"'),
    (r'NFC PCB天线，(\d+)匝，VG([\d.]+) RD专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, VG{m.group(2)} RD'),
    (r'NFC PCB天线，(\d+)匝，IKEA (\d+\.?\d*)寸标准款专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, IKEA {m.group(2)}", Standard'),
    (r'NFC PCB天线，(\d+)匝，IKEA (\d+\.?\d*)寸专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, IKEA {m.group(2)}"'),
    (r'NFC PCB天线，(\d+)匝，(\d+\.?\d*)寸标准款专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, Standard {m.group(2)}"'),
    (r'NFC PCB天线，(\d+)匝，(\d+\.?\d*)寸专用',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, for {m.group(2)}"'),
    (r'NFC PCB天线，(\d+)匝，(.*)',
     lambda m: f'NFC PCB Antenna, {m.group(1)} Turns, {_translate_desc(m.group(2))}'),
    (r'VG(\d+\.?\d*)寸标准款专用', lambda m: f'Standard VG{m.group(1)}"'),
    (r'VG(\d+\.?\d*)寸超薄款专用', lambda m: f'Ultra-Thin VG{m.group(1)}"'),
    (r'VG([\d.]+) RD专用', lambda m: f'VG{m.group(1)} RD'),
    (r'IKEA (\d+\.?\d*)寸专用', lambda m: f'IKEA {m.group(1)}"'),
    (r'(\d+\.?\d*)寸专用', lambda m: f'for {m.group(1)}"'),
    (r'(\d+\.?\d*)寸', lambda m: f'{m.group(1)}"'),
    (r'(\d+)匝', lambda m: f'{m.group(1)} Turns'),
    (r'FPC连接器，下接，间距([\d.]+)mm，max高([\d.]+)(?:mm)?',
     lambda m: f'FPC Connector, Bottom Contact, Pitch {m.group(1)}mm, max Height {m.group(2)}mm'),
]

MANUF_RE = re.compile(r'([A-Za-z0-9_\-./+]+)\(([^)]*[一-鿿][^)]*)\)')


def _translate_desc(text):
    for cn, en in sorted(TRANSLATIONS.items(), key=lambda x: -len(x[0])):
        if cn in text:
            text = text.replace(cn, en)
    text = text.replace('，', ', ')
    text = text.replace('、', ', ')
    text = text.replace('。', '. ')
    return text


def translate_text(text):
    if not text or not any('一' <= c <= '鿿' for c in text):
        return text
    for pattern, repl in PATTERNS:
        try:
            new_text = re.sub(pattern, repl, text)
            if new_text != text:
                text = new_text
        except:
            continue
    text = _translate_desc(text)
    text = MANUF_RE.sub(r'\1', text)
    if any('一' <= c <= '鿿' for c in text):
        for pattern, repl in PATTERNS:
            try:
                new_text = re.sub(pattern, repl, text)
                if new_text != text:
                    text = new_text
            except:
                continue
    if any('一' <= c <= '鿿' for c in text):
        text = _translate_desc(text)
    text = re.sub(r'专用', '', text)
    text = re.sub(r'[，、。；：？！]', ' ', text)
    text = re.sub(r'  +', ' ', text).strip()
    text = text.rstrip(',').strip()
    return text


def apply_translation_same_size(data):
    """
    Find and translate Chinese in Data stream using same-size in-place replacement.
    Only modifies a field if the translated text fits within the original byte length.
    Returns modified data (same size as input) or None if no change.
    """
    text_latin = data.decode('latin-1')
    utf8_fields = re.findall(r'\|%UTF8%(\w+)=([^|]*?)(?=\||\x00)', text_latin)

    modified = bytearray(data)
    any_change = False

    for field_key, field_val_latin in utf8_fields:
        raw_bytes = field_val_latin.encode('latin-1')
        try:
            chinese_text = raw_bytes.decode('utf-8')
        except:
            continue

        if not any('一' <= c <= '鿿' for c in chinese_text):
            continue

        translated = translate_text(chinese_text)
        if translated == chinese_text:
            continue

        # Only proceed if translated value fits in original byte length
        new_val_utf8 = translated.encode('utf-8')
        old_len = len(raw_bytes)
        new_len = len(new_val_utf8)

        if new_len > old_len:
            # Translation too long for same-size constraint
            # Pad with spaces up to old_len and truncate as needed
            if old_len <= 4:
                continue  # too short to bother
            # Try to fit by abbreviating: replace common long words
            abbreviated = translated
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Connector', 'Conn.', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Standard', 'Std', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Inverted-F', 'Inv-F', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Antenna', 'Ant', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Ferrite Bead', 'FB', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Spring', 'Spr', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Positive', 'Pos', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Negative', 'Neg', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Schottky', 'Sch', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                abbreviated = re.sub(r'Bidirectional', 'BiDir', abbreviated)
            if len(abbreviated.encode('utf-8')) > old_len:
                # Still too long - truncate to fit
                truncated = abbreviated.encode('utf-8')[:old_len]
                # Try not to break UTF-8 sequence
                while truncated and truncated[-1] & 0xC0 == 0x80:
                    truncated = truncated[:-1]
                abbreviated = truncated.decode('utf-8', errors='replace')
            new_val_utf8 = abbreviated.encode('utf-8')
            new_len = len(new_val_utf8)
            if new_len > old_len:
                continue  # skip this field

        # --- Replace UTF-8 field value ---
        pattern = f'|%UTF8%{field_key}={field_val_latin}|'
        new_field = f'|%UTF8%{field_key}='.encode('latin-1') + new_val_utf8 + b'|'

        idx = modified.find(pattern.encode('latin-1'))
        if idx >= 0:
            field_len = len(pattern.encode('latin-1'))
            new_field_len = len(new_field)
            if new_field_len == field_len:
                modified[idx:idx + field_len] = new_field
            elif new_field_len < field_len:
                modified[idx:idx + field_len] = new_field + b'\x00' * (field_len - new_field_len)
            else:
                modified[idx:idx + field_len] = new_field[:field_len]
            any_change = True

        # --- Replace corresponding GBK field ---
        # Search forward from the modified UTF-8 field position
        search_start = idx if idx >= 0 else 0
        rest = modified[search_start:].decode('latin-1')
        plain_pattern = f'|{field_key}='
        plain_idx = rest.find(plain_pattern)
        if plain_idx < 0:
            continue

        val_start = plain_idx + len(plain_pattern)
        val_end = len(rest)
        for j in range(val_start, min(val_start + 500, len(rest))):
            if rest[j] in '|\x00':
                val_end = j
                break

        old_val = rest[val_start:val_end].encode('latin-1')
        try:
            gbk_text = old_val.decode('gbk')
        except:
            continue

        if not any('一' <= c <= '鿿' for c in gbk_text):
            continue

        gbk_translated = translate_text(gbk_text)
        if gbk_translated == gbk_text:
            continue

        gbk_bytes = gbk_translated.encode('gbk')
        byte_offset = search_start + val_start
        old_len_gbk = len(old_val)
        new_len_gbk = len(gbk_bytes)

        if new_len_gbk > old_len_gbk:
            # Try abbreviation
            gbk_abbrev = gbk_translated
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Connector', 'Conn.', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Standard', 'Std', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Inverted-F', 'Inv-F', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Antenna', 'Ant', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Ferrite Bead', 'FB', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Spring', 'Spr', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Positive', 'Pos', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Negative', 'Neg', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Schottky', 'Sch', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                gbk_abbrev = re.sub(r'Bidirectional', 'BiDir', gbk_abbrev)
            if len(gbk_abbrev.encode('gbk')) > old_len_gbk:
                truncated = gbk_abbrev.encode('gbk')[:old_len_gbk]
                while truncated and truncated[-1] & 0x80:
                    truncated = truncated[:-1]
                gbk_abbrev = truncated.decode('gbk', errors='replace')
            gbk_bytes = gbk_abbrev.encode('gbk')
            new_len_gbk = len(gbk_bytes)
            if new_len_gbk > old_len_gbk:
                continue

        if new_len_gbk == old_len_gbk:
            modified[byte_offset:byte_offset + old_len_gbk] = gbk_bytes
        elif new_len_gbk < old_len_gbk:
            modified[byte_offset:byte_offset + old_len_gbk] = gbk_bytes + b'\x00' * (old_len_gbk - new_len_gbk)
        else:
            modified[byte_offset:byte_offset + old_len_gbk] = gbk_bytes[:old_len_gbk]
        any_change = True

    return bytes(modified) if any_change else None


def process_one_schlib(filepath):
    """Process a single SchLib file. Returns (modified, total_translations)."""
    basename = os.path.basename(filepath)
    print(f"\n{'='*60}")
    print(f"Processing: {basename}")
    print(f"{'='*60}")

    # Backup
    backup = filepath + ".bak"
    if not os.path.exists(backup):
        print(f"  Creating backup: {os.path.basename(backup)}")
        shutil.copy2(filepath, backup)
    else:
        print(f"  Backup exists, skipping: {os.path.basename(backup)}")

    print(f"  Opening...")
    ole = olefile.OleFileIO(filepath, write_mode=True)

    modified_count = 0
    translated_fields = []

    for stream_path in ole.listdir():
        path = '/'.join(stream_path)
        if not path.endswith('/Data'):
            continue

        data = ole.openstream(path).read()

        # Quick check for Chinese
        text_latin = data.decode('latin-1')
        utf8_fields = re.findall(r'\|%UTF8%(\w+)=([^|]*?)(?=\||\x00)', text_latin)
        utf8_fields_raw = [fv for _, fv in utf8_fields]
        has_cn = False
        for _, fv in utf8_fields:
            try:
                decoded = fv.encode('latin-1').decode('utf-8')
                if any('一' <= c <= '鿿' for c in decoded):
                    has_cn = True
                    break
            except:
                continue

        if not has_cn:
            continue

        modified_data = apply_translation_same_size(data)
        if modified_data:
            if len(modified_data) != len(data):
                print(f"  ERROR: {path} size changed")
                continue

            ole.write_stream(path, modified_data)
            modified_count += 1

            # Collect translation info
            new_latin = modified_data.decode('latin-1')
            new_matches = list(re.finditer(r'\|%UTF8%(\w+)=([^|]*?)(?=\||\x00)', new_latin))
            for ni, nm in enumerate(new_matches):
                fk = nm.group(1)
                try:
                    decoded = nm.group(2).encode('latin-1').decode('utf-8')
                    if ni < len(utf8_fields_raw):
                        orig_val_raw = utf8_fields_raw[ni]
                        orig_decoded = orig_val_raw.encode('latin-1').decode('utf-8', errors='replace')
                        if orig_decoded.rstrip('\x00').rstrip() != decoded.rstrip('\x00').rstrip():
                            translated_fields.append((path.split('/')[0], fk, orig_decoded[:60], decoded[:60]))
                except:
                    pass

    ole.close()

    print(f"  Components modified: {modified_count}")
    print(f"  Field translations: {len(translated_fields)}")
    for name, fk, old, new in translated_fields[:20]:
        print(f"    [{name}] {fk}: {old} -> {new}")
    if len(translated_fields) > 20:
        print(f"    ... and {len(translated_fields) - 20} more")

    return modified_count > 0, len(translated_fields)


def main():
    """Main function."""
    if not SCHLIB_FILES:
        print("No *.SchLib files found in script directory.")
        print(f"Directory: {SCRIPT_DIR}")
        sys.exit(1)

    print(f"Found {len(SCHLIB_FILES)} SchLib file(s) to process:")
    for f in SCHLIB_FILES:
        print(f"  {os.path.basename(f)}")

    total_modified = 0
    total_translations = 0

    for filepath in SCHLIB_FILES:
        modified, count = process_one_schlib(filepath)
        if modified:
            total_modified += 1
        total_translations += count

    print(f"\n{'='*60}")
    print(f"Summary: {total_modified}/{len(SCHLIB_FILES)} files modified, {total_translations} total field translations")
    print("All done!")


if __name__ == '__main__':
    main()
