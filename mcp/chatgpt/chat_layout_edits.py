"""Keep Claude's unobstructive dock, but require room for an actual answer."""


def edits():
    return [
        ('if (bandB - bandT >= 130 && bandR - bandL >= 360)',
         'if (bandB - bandT >= 360 && bandR - bandL >= 360)', 1),
    ]
