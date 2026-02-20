#!/usr/bin/env python3
import re

def update_po_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match msgid and msgstr blocks
    pattern = r'(msgid\s+"(?:[^"\\]|\\.)*"\s*\n(?:\s*"[^"\\]*"\s*\n)*)\s*(msgstr\s+"(?:[^"\\]|\\.)*"\s*\n(?:\s*"[^"\\]*"\s*\n)*)'

    def replace_msgstr(match):
        msgid_block = match.group(1)
        msgstr_block = match.group(2)

        # Extract the msgid content
        msgid_lines = msgid_block.strip().split('\n')
        msgid_content = []
        for line in msgid_lines:
            if line.startswith('msgid '):
                msgid_content.append(line[7:-1])  # Remove 'msgid "' and '"'
            elif line.startswith('"') and line.endswith('"'):
                msgid_content.append(line[1:-1])  # Remove surrounding quotes

        # Join the msgid content
        msgid_text = ''.join(msgid_content)

        # Check if msgstr is empty (only "")
        msgstr_lines = msgstr_block.strip().split('\n')
        msgstr_content = []
        for line in msgstr_lines:
            if line.startswith('msgstr '):
                msgstr_content.append(line[8:-1])  # Remove 'msgstr "' and '"'
            elif line.startswith('"') and line.endswith('"'):
                msgstr_content.append(line[1:-1])

        msgstr_text = ''.join(msgstr_content).strip()

        if not msgstr_text:  # If msgstr is empty, copy msgid
            # Format the msgid_text back into msgstr format
            if msgid_text:
                # Split into lines if necessary
                lines = msgid_text.split('\n')
                new_msgstr = 'msgstr "' + lines[0] + '"\n'
                for line in lines[1:]:
                    new_msgstr += '        "' + line + '"\n'
                new_msgstr = new_msgstr.rstrip() + '\n'
            else:
                new_msgstr = 'msgstr ""\n'
            return msgid_block + new_msgstr
        else:
            return match.group(0)  # Leave as is

    updated_content = re.sub(pattern, replace_msgstr, content, flags=re.MULTILINE | re.DOTALL)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

if __name__ == "__main__":
    update_po_file('/opt/odoo/odoo17/custom-addons/sandor_it_inventory/i18n/es_CO.po')