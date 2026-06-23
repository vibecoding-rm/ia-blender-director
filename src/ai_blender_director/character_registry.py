from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterDefinition:
    asset_id: str
    label: str
    keywords: tuple[str, ...]


CHARACTERS: tuple[CharacterDefinition, ...] = (
    CharacterDefinition("humbrete_v1", "Humbrete", ("humbrete", "humbertico", "humberto", "sabueso", "fiscal", "bulldog")),
    CharacterDefinition("michelito_v1", "Michelito Filo", ("michelito", "michel", "con filo", "gallito", "gallo", "navaja")),
    CharacterDefinition("gaby_v1", "Gaby Filo", ("gaby", "gabriela", "lechuza", "buho", "b\u00faho", "teleprompter", "matriz de opinion", "matriz de opini\u00f3n")),
    CharacterDefinition("randy_v1", "Randy Redondo", ("randy", "mesa redonda", "tortuga", "redondo", "decano")),
    CharacterDefinition("arleen_v1", "Arleen Chapea", ("arleen", "chapea", "chapeando", "jutia", "jut\u00eda", "podadora", "tijeras")),
    CharacterDefinition("brigada_v1", "Brigada Copy-Paste", ("brigada", "copy-paste", "copypaste", "clones", "teclado", "minions")),
    CharacterDefinition("lazaro_v1", "L\u00e1zaro Mediod\u00eda", ("lazaro", "l\u00e1zaro", "mediodia", "mediod\u00eda", "huron", "hur\u00f3n", "ultima hora", "\u00faltima hora")),
    CharacterDefinition("pupila_v1", "Fantasma de la Pupila", ("pupila", "fantasma", "retrato", "iroel", "insomne")),
    CharacterDefinition("guerrero_v1", "Guerrero de Lata", ("guerrero", "lata", "anonimo", "an\u00f3nimo", "casco", "armadura", "caballero")),
    CharacterDefinition("guanajo_v1", "El Guanajo Designado", ("guanajo", "designado", "diaz-canel", "diazcanel", "canel", "presidente", "pavo", "singao")),
    CharacterDefinition("caiman_v1", "El Caim\u00e1n General", ("caiman", "caim\u00e1n", "cocodrilo", "raul", "ra\u00fal", "general", "titiritero", "hilos")),
    CharacterDefinition("chivaton_v1", "Gerardo el Chivat\u00f3n", ("chivaton", "chivat\u00f3n", "gerardo", "cdr", "chivo", "vigilante", "binoculares")),
    CharacterDefinition("marrero_v1", "Marrero el Conserje 5 Estrellas", ("marrero", "conserje", "hotel", "hoteles", "cinco estrellas", "pavo real")),
    CharacterDefinition("bruno_v1", "Bruno Bloqueo", ("bruno", "bloqueo", "canciller", "maja", "maj\u00e1", "diplomatico", "diplom\u00e1tico")),
    CharacterDefinition("trovador_v1", "Trovador del Picadillo", ("trovador", "picadillo", "soya", "guitarra", "cancion", "canci\u00f3n", "sinsonte")),
    CharacterDefinition("ciberclarias_v1", "Ciberclarias", ("ciberclaria", "ciberclarias", "troll", "enjambre", "claria", "bagre")),
    CharacterDefinition("comandante_cerdo_v1", "Comandante Cerdo", ("cerdo", "comandante", "portavoz", "pig")),
    CharacterDefinition("cotorra_v1", "La Cotorra", ("cotorra", "mascota", "loro", "parrot")),
    CharacterDefinition("protagonista_v1", "Protagonista Proxy", ("protagonista_v1", "protagonista v1", "proxy", "placeholder")),
    CharacterDefinition("protagonista_v2", "Protagonista", ("protagonista", "protagonista_v2", "protagonista v2", "personaje", "character", "hero", "heroe", "h\u00e9roe", "soldier")),
)


def character_asset_ids() -> tuple[str, ...]:
    return tuple(c.asset_id for c in CHARACTERS)


def character_schema_text() -> str:
    return ", ".join(f"{c.asset_id} ({c.label})" for c in CHARACTERS) + ", or null"


def detect_character(prompt: str) -> str | None:
    normalized = _normalize_text(prompt)
    for character in CHARACTERS:
        if character.asset_id in normalized:
            return character.asset_id
    for character in CHARACTERS:
        if any(_normalize_text(keyword) in normalized for keyword in character.keywords):
            return character.asset_id
    return None


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.strip().lower())
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(ascii_text.split())
