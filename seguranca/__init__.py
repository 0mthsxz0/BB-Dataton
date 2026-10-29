"""Base municipal de segurança: observações ausentes nunca são zeros."""

# O contrato existente do motor fica em politica_motor; os coletores usam submódulos.
from .politica_motor import avaliar_seguranca, verificar_snapshot, POLITICA_SEGURANCA, UF_PREFIXOS
