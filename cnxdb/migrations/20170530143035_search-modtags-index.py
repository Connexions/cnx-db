# -*- coding: utf-8 -*-


def up(cursor):
    cursor.execute('CREATE INDEX moduletags_module_ident_idx '
                   'on moduletags (module_ident)')

def down(cursor):
    cursor.execute('DROP INDEX moduletags_module_ident_idx')
