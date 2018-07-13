# Use <m> or <message> to retrieve the data transmitted by the scanner.
# Use <t> or <terminal> to retrieve the running terminal browse record.
# Put the returned action code in <act>, as a single character.
# Put the returned result or message in <res>, as a list of strings.
# Put the returned value in <val>, as an integer

act = 'L'
res = [
    ('|', 'List step'),
    ('error', 'Go to Error step'),
    ('continue', 'Go to next step'),
]
