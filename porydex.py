import argparse
import json
import pathlib
import os

import porydex.config

from porydex.common import PICKLE_PATH
from porydex.parse.abilities import parse_abilities
from porydex.parse.encounters import parse_encounters
from porydex.parse.form_tables import parse_form_tables
from porydex.parse.items import parse_items
from porydex.parse.learnsets import parse_level_up_learnsets, parse_teachable_learnsets
from porydex.parse.maps import parse_maps
from porydex.parse.moves import parse_moves
from porydex.parse.species import parse_species

def config_show(_):
    porydex.config.load()
    print(f'compiler command:  {str(porydex.config.compiler)}')
    print(f'path to expansion: {str(porydex.config.expansion)}')
    print(f'output directory:  {str(porydex.config.output)}')

def config_set(args):
    if args.expansion:
        assert args.expansion.resolve().exists(), f'specified expansion directory {args.expansion} does not exist'
        porydex.config.expansion = args.expansion.resolve()

    if args.compiler:
        porydex.config.compiler = args.compiler

    if args.output:
        porydex.config.output = args.output.resolve()

    porydex.config.save()

def config_clear(_):
    porydex.config.clear()

def extract(args):
    if args.reload:
        for f in PICKLE_PATH.glob('*'):
            os.remove(f)

    porydex.config.load()

    [path.mkdir(parents=True) if not path.exists() else () for path in (PICKLE_PATH, porydex.config.output)]

    expansion_data = porydex.config.expansion / 'src' / 'data'
    custom_headers = pathlib.Path('custom_headers')
    moves = parse_moves(expansion_data / 'moves_info.h')
    move_names = [move['name'] for move in sorted(moves.values(), key=lambda m: m['num'])]

    abilities = parse_abilities(expansion_data / 'abilities.h')
    items = parse_items(expansion_data / 'items.h')
    forms = parse_form_tables(expansion_data / 'pokemon' / 'form_species_tables.h')
    map_sections = parse_maps(expansion_data / 'region_map' / 'region_map_entries.h')
    lvlup_learnsets = parse_level_up_learnsets(custom_headers / 'level_up_learnsets.h', move_names)
    teach_learnsets = parse_teachable_learnsets(expansion_data / 'pokemon' / 'teachable_learnsets.h', move_names)

    species = parse_species(
        expansion_data / 'pokemon' / 'species_info.h',
        abilities,
        items,
        move_names,
        forms,
        map_sections,
        lvlup_learnsets,
        teach_learnsets,
    )
    species_names = [mon['name'] for mon in sorted(species.values(), key=lambda m: m['num'])]
    encounters = parse_encounters(expansion_data / 'wild_encounters.h', species_names)

    with open(porydex.config.output / 'moves.json', 'w', encoding='utf-8') as outf:
        json.dump(moves, outf, indent=4)

    with open(porydex.config.output / 'species.json', 'w', encoding='utf-8') as outf:
        json.dump(species, outf, indent=4)

    with open(porydex.config.output / 'encounters.json', 'w', encoding='utf-8') as outf:
        json.dump(encounters, outf, indent=4)

def main():
    argp = argparse.ArgumentParser(prog='porydex',
                                   description='generate data exports from pokeemerald-expansion for showdown dex')
    subp = argp.add_subparsers(required=True)

    config_p = subp.add_parser('config', help='configuration options for porydex')
    config_subp = config_p.add_subparsers(required=True)

    config_show_p = config_subp.add_parser('show', help='show configured options for porydex')
    config_show_p.set_defaults(func=config_show)

    config_set_p = config_subp.add_parser('set', help='set configurable options for porydex')
    config_set_p.add_argument('-e', '--expansion', action='store',
                              help='path to the root of your pokeemerald-expansion repository; default: ../pokeemerald-expansion',
                              type=pathlib.Path)
    config_set_p.add_argument('-c', '--compiler', action='store',
                              help='command for or path to the compiler to be used for pre-processing; default: gcc',
                              type=pathlib.Path)
    config_set_p.add_argument('-o', '--output', action='store',
                              help='path to output directory for extracted data files; default: ./out',
                              type=pathlib.Path)
    config_set_p.set_defaults(func=config_set)

    config_clear_p = config_subp.add_parser('clear', help='clear configured options')
    config_clear_p.set_defaults(func=config_clear)

    extract_p = subp.add_parser('extract', help='run data extraction')
    extract_p.add_argument('--reload', action='store_true',
                           help='if specified, flush the cache of parsed data and reload from expansion')
    extract_p.set_defaults(func=extract)

    args = argp.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

