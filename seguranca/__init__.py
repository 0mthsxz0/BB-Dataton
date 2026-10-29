"""Base municipal de segurança: observações ausentes nunca são zeros."""

# Compatibilidade com os imports da main; não exige copiar seguranca.py sobre o pacote.
from .politica_motor import avaliar_seguranca, verificar_snapshot, POLITICA_SEGURANCA, UF_PREFIXOS
