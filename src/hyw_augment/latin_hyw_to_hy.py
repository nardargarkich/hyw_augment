"""
Western Armenian Latin-to-Armenian romanization mapping for hyw_augment.

Principles:
- Made for natural Latin keyboard input by Western Armenian speakers
- Digraphs checked before single characters (longest match first)
- Ambiguous mappings (where WArm consonant mergers collapse distinctions)
  return multiple candidates for downstream disambiguation
- Word-boundary allograph rules handled separately from the core table

Usage:
    from romanization import MAPPING, AMBIGUOUS, WORD_INITIAL_RULES
"""

# Armenian characters by Unicode codepoint, for reference and readability.
_ = chr

# ── Core mapping table ──────────────────────────────────────────────
# Each entry: (latin_input, [armenian_candidates], notes)
#
# Single-candidate entries are unambiguous.
# Multi-candidate entries are where WArm mergers create real ambiguity
# that must be resolved by the morphological analyzer / LM.
#
# Sorted longest-first within each group for greedy matching.

MAPPING = [
    # ── Digraphs and trigraphs (check these first) ──────────────────

    # Alveolar affricates
    ("ts",  [_(0x056E), _(0x0581)],  "AMBIG: tsa/tso - ծ or ց"),
    ("dz",  [_(0x0571)],             "dza  - voiced alveolar affricate"),

    # Postalveolar affricates — ch maps to the pair people actually confuse
    ("ch",  [_(0x057B), _(0x0579)],  "AMBIG: jheh/ch'a - ջ or չ"),

    # Fricatives
    ("sh",  [_(0x0577)],             "sha  - voiceless postalveolar fricative"),
    ("zh",  [_(0x056A)],             "zhe  - ժ (also reachable via j)"),
    ("gh",  [_(0x0572)],             "ghat - voiced velar fricative"),
    ("kh",  [_(0x056D)],             "xe   - voiceless velar fricative"),

    # Common digraph for ու (single vowel sound in Armenian)
    ("ou",  [_(0x0578) + _(0x0582)], "u vowel - ու"),
    ("u",   [_(0x0578) + _(0x0582), _(0x0568)],
                                     "AMBIG: u vowel (ու) or schwa (ը) - alias for both"),

    # digraph "rr" sometimes used to disambiguate ռ from ր, but many writers just use "r" for both
    ("rr",  [_(0x057C)],             "ra  - ռ (explicit disambiguation from r)"),
    ("r",   [_(0x0580), _(0x057C)],  "AMBIG: re/ra - ր or ռ (both just 'r' in typing)"),

    # Yev
    ("yev", [_(0x0587)],             "yev ligature - եւ"),
    ("ev",  [_(0x0587)],             "yev ligature - եւ ((medial) alias)"),

    # ── Single characters ───────────────────────────────────────────

    # Vowels
    ("a",   [_(0x0561)],             "ayb  - ա"),
    ("e",   [_(0x0565), _(0x0567)],  "AMBIG: yech/e - ե or է"),
    ("i",   [_(0x056B)],             "ini  - ի"),
    ("o",   [_(0x0585), _(0x0578)],  "AMBIG: o/vo - օ or ո"),

    # Unambiguous consonants
    ("m",   [_(0x0574)],             "men  - մ"),
    ("n",   [_(0x0576)],             "nou  - ն"),
    ("l",   [_(0x056C)],             "liwn - լ"),
    ("v",   [_(0x057E)],             "vew  - վ"),
    ("h",   [_(0x0570)],             "ho   - հ"),
    ("y",   [_(0x0575)],             "hi   - յ"),
    ("j",   [_(0x056A), _(0x0573)],  "AMBIG: zhe/che - ժ or ճ"),
    ("f",   [_(0x0586)],             "fe   - ֆ"),

    # Schwa - ը (ut). Multiple conventions in diaspora texting:
    # "@", "uh", or even the actual Armenian letter ը inline in Latin text.
    # The literal ը passthrough is handled separately (not in this table).
    ("uh",  [_(0x0568)],             "ut   - ը (schwa, digraph variant)"),
    ("@",   [_(0x0568)],             "ut   - ը (schwa, @ convention)"),

    # ── The big ambiguities: WArm consonant shift mergers ───────────
    # In WArm pronunciation, these pairs are (near-)identical.
    # Latin input reflects pronunciation, not spelling.

    # s-series: ս [s] vs զ [z] in WArm
    ("s",   [_(0x057D), _(0x0566)],  "AMBIG: s/sez - ս or զ (both [s] in WArm)"),
    ("z",   [_(0x0566)],             "za   - զ ([z] in WArm)"),

    # k-series: կ [g] vs ք [k] vs գ [k] in WArm
    ("k",   [_(0x0584), _(0x0563)],  "AMBIG: k'e/kim - ք or գ (both [k] in WArm)"),
    ("g",   [_(0x056F)],             "gen  - կ ([g] in WArm)"),

    # t-series: թ [t] vs դ [t] in WArm
    ("t",   [_(0x0569), _(0x0564)],  "AMBIG: t'o/da - թ or դ (both [t] in WArm)"),
    ("d",   [_(0x057F)],             "diwn - տ ([d] in WArm)"),

    # p-series: փ [p] vs բ [p] in WArm
    ("p",   [_(0x0583), _(0x0562)],  "AMBIG: p'iwr/ben - փ or բ (both [p] in WArm)"),
    ("b",   [_(0x057A)],             "ben  - պ ([b] in WArm)"),

    # c as alternate input - can mean ts-sounds OR k-sounds depending on writer
    ("c",   [_(0x0581), _(0x056E), _(0x0584), _(0x0563)],
                                     "AMBIG: c'o/tsa/k'e/kim - ց or ծ or ք or գ"),

    # q - less common, but some writers use it
    ("q",   [_(0x0584), _(0x0563)],  "AMBIG: k'e/kim - ք or (rarely) գ"),

    # w as alternate for v (some typists)
    ("w",   [_(0x057E)],             "vew  - վ (alias)"),

    # x as alternate for kh
    ("x",   [_(0x056D)],             "xe   - խ (alias)"),
]


# ── Word-boundary allograph rules ───────────────────────────────────
# These generate positional variants in the lattice.
# Applied AFTER the core mapping, based on position in word.

WORD_INITIAL_RULES = {
    # Word-initial ե sounds like "ye", mid-word like "e"
    # So initial "e" should also try ե (which implies ye- at start)
    # and է (which is always just [ɛ])
    "e_initial": "generate_both",

    # Word-initial ո sounds like "vo" in WArm
    # So initial "o" should try ո (= vo-) and օ (= o-)
    "o_initial": "generate_both",

    # Word-initial "y" before vowel may be implicit in ե
    # like in "yes" - word-initial yech already encodes the y- sound
    "y_before_vowel_initial": "check_if_ե_covers_it",

    # Word-initial յ is pronounced [h] in WArm
    # So initial "h" should try յ and հ
    "h_initial": "generate_both",
}


# ── Convenience accessors ───────────────────────────────────────────

def get_mapping_dict():
    """Return as a dict of latin_key -> list of armenian candidates.
    Preserves insertion order (longest first within groups)."""
    return {lat: arm for lat, arm, _ in MAPPING}


def get_ambiguous_keys():
    """Return the set of latin keys that produce multiple candidates."""
    return {lat for lat, arm, _ in MAPPING if len(arm) > 1}


def get_sorted_keys():
    """Return latin keys sorted longest-first for greedy matching."""
    return sorted([lat for lat, _, _ in MAPPING], key=len, reverse=True)


# ── Quick sanity check ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Western Armenian Romanization Table ===\n")

    sorted_entries = sorted(MAPPING, key=lambda x: (-len(x[0]), x[0]))

    for lat, arms, note in sorted_entries:
        candidates = " / ".join(arms)
        ambig = " [AMBIG]" if len(arms) > 1 else ""
        print(f"  {lat:>4s} → {candidates}{ambig}  ({note})")

    print(f"\nTotal entries: {len(MAPPING)}")
    print(f"Ambiguous: {len(get_ambiguous_keys())}")
    print(f"Keys (longest first): {get_sorted_keys()[:10]}...")