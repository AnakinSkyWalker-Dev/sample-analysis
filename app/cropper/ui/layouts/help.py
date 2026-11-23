from __future__ import annotations

from tkinter import ttk


def build_help_layout(_app: object, parent: ttk.Frame) -> None:
    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 14))
    ttk.Label(header, text="Ajuda e guia rápido", style="Title.TLabel").pack(
        anchor="w"
    )
    ttk.Label(
        header,
        text="Instruções para analisar, revisar, montar e salvar suas imagens.",
        style="Muted.TLabel",
    ).pack(anchor="w", pady=(3, 0))

    content = ttk.Frame(parent)
    content.pack(fill="both", expand=True)
    content.columnconfigure(0, weight=1, uniform="help")
    content.columnconfigure(1, weight=1, uniform="help")

    def card(
        row: int,
        column: int,
        title: str,
        body: str,
    ) -> None:
        panel = ttk.Frame(content, style="Panel.TFrame", padding=(16, 14))
        panel.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0, 7) if column == 0 else (7, 0),
            pady=(0, 12),
        )
        ttk.Label(panel, text=title, style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            panel,
            text=body,
            style="CardMuted.TLabel",
            justify="left",
            wraplength=480,
        ).pack(anchor="w", fill="x", pady=(8, 0))

    card(
        0,
        0,
        "1 · Preparar e analisar",
        "Na aba Corte de amostras, escolha a pasta principal que contém as "
        "pastas Vidro, MDF e Cerâmica. Clique em Analisar fotos. A pasta "
        "imgs_results é ignorada automaticamente.",
    )
    card(
        0,
        1,
        "2 · Revisar e marcar",
        "Selecione o material e uma foto na lista para conferir a detecção. "
        "Use Ctrl + roda do mouse ou os controles de zoom. Se faltar um "
        "quadrado, use Adicionar quadrado; para marcar novamente todos, use "
        "Marcar quadrados e clique nos quatro cantos.",
    )
    card(
        1,
        0,
        "3 · Gerar recortes",
        "Clique em Cortar fotos identificadas para salvar em out, mantendo "
        "as pastas originais. Se houver arquivos com o mesmo nome, escolha "
        "se deseja substituí-los. O botão Abrir out acessa os resultados.",
    )
    card(
        1,
        1,
        "4 · Montar uma prancha",
        "Na aba Montagem de imagem, filtre ou pesquise as fotos de out. "
        "Selecione uma foto, escolha a posição A–F e clique em Usar foto. "
        "O botão ↻ junto à foto gira apenas essa imagem; o ↻ na prévia gira "
        "a montagem inteira. Clique em Salvar montagem para exportar.",
    )
    card(
        2,
        0,
        "Qualidade ou desempenho",
        "Use o seletor Prévia no topo da janela. Qualidade aplica "
        "redimensionamento de alta qualidade e nitidez leve; Desempenho "
        "prioriza rapidez ao atualizar as prévias. A escolha é salva e "
        "afeta somente a visualização, não os arquivos exportados.",
    )
    card(
        2,
        1,
        "Dados e atalhos",
        "A análise e as marcações concluídas são salvas no cache. A opção "
        "Preservar fotos prontas evita reanalisar itens finalizados; fotos "
        "alteradas ou em revisão continuam sendo verificadas. Atalhos podem "
        "ser consultados e alterados na aba Atalhos.",
    )
    card(
        3,
        0,
        "5 · Ampliar etiquetas",
        "Na aba Etiquetas A–F, analise imgs_results para visualizar os "
        "quadrados detectados. Confirme a ação para ampliar as etiquetas "
        "e substituir os arquivos originais.",
    )
    card(
        3,
        1,
        "6 · Organizar nomes",
        "Use Organizar nomes no topo para conferir a prévia e renomear "
        "arquivos de imgs_results. As pastas são preservadas; nomes sem "
        "código reconhecido ou com conflito não são alterados.",
    )
    card(
        4,
        0,
        "7 · Montagem 4×3",
        "Em Montagem de imagem, clique em Montagem 4×3 e escolha a foto. "
        "Confira as etiquetas A–D na prévia, arraste os cantos para corrigir "
        "a detecção ou marque quatro pontos. Ajuste o espaçamento e salve a "
        "prancha em imgs_results/Montagens.",
    )
