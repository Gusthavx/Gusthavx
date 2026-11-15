"""Gera o dash visual do perfil (dash/escuro.svg e dash/claro.svg).

Conta os commits direto em cada repositório (inclusive os privados), porque o
calendário do GitHub deixa os privados de fora. Usa o `gh` já logado; nenhum
nome de repositório privado vai para a imagem, só os números somados.

Uso: python dash/gerar.py
"""
import json, subprocess, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

USUARIO = "Gusthavx"
FUSO = ZoneInfo("America/Bahia")
FORA_DOS_COMMITS = {"Gusthavx"}            # o próprio perfil (atualização automática)
FORA_DAS_LINGUAGENS = {"sms-hub", "ares-mind", "Gusthavx"}  # cofres de notas, não são código
AQUI = Path(__file__).resolve().parent
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def coletar():
    q = """{ user(login:"%s"){ followers{totalCount}
      repositories(ownerAffiliations:OWNER,first:100,isFork:false,orderBy:{field:PUSHED_AT,direction:DESC}){
        nodes{ name isPrivate stargazerCount pushedAt primaryLanguage{name color}
          languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}} } } } }""" % USUARIO
    u = json.loads(gh("api", "graphql", "-f", "query=" + q))["data"]["user"]
    repos = u["repositories"]["nodes"]
    hoje = dt.datetime.now(FUSO).date()
    inicio = hoje - dt.timedelta(days=371)
    desde = dt.datetime.combine(inicio, dt.time(), FUSO).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    por_dia = Counter()
    for r in repos:
        if r["name"] in FORA_DOS_COMMITS:
            continue
        try:
            out = gh("api", "--paginate", f"repos/{USUARIO}/{r['name']}/commits?since={desde}&per_page=100",
                     "--jq", ".[].commit.author.date")
        except RuntimeError:
            continue  # repositório vazio
        for linha in out.split():
            d = dt.datetime.fromisoformat(linha.replace("Z", "+00:00")).astimezone(FUSO).date()
            por_dia[d] += 1
    linguas, cores = Counter(), {}
    for r in repos:
        if r["name"] in FORA_DAS_LINGUAGENS:
            continue
        for e in r["languages"]["edges"]:
            linguas[e["node"]["name"]] += e["size"]
            cores[e["node"]["name"]] = e["node"]["color"] or "#888"
    return {
        "hoje": hoje, "por_dia": por_dia, "linguas": linguas, "cores": cores,
        "repos": len(repos), "privados": sum(r["isPrivate"] for r in repos),
        "estrelas": sum(r["stargazerCount"] for r in repos), "seguidores": u["followers"]["totalCount"],
        "recentes": [(r["name"], (r["primaryLanguage"] or {}).get("color") or "#888") for r in repos if not r["isPrivate"] and r["name"] not in FORA_DOS_COMMITS][:3],
    }


TEMAS = {
    "escuro": dict(bg="#0b0b0d", card="#151518", linha="#26262b", fg="#f2f2f2", mut="#8e8e93", tint="#ff5b24",
                   calor=["#1e1e22", "#4a1f10", "#8a3314", "#cf4519", "#ff5b24"]),
    "claro": dict(bg="#ffffff", card="#f5f5f7", linha="#e5e5ea", fg="#111111", mut="#6e6e73", tint="#ff5b24",
                  calor=["#ebebef", "#ffd4c4", "#ffa480", "#ff7b4b", "#ff5b24"]),
}


def br(n):
    return f"{n:,}".replace(",", ".")


def sequencias(por_dia, hoje):
    atual, d = 0, hoje
    if por_dia[d] == 0:
        d -= dt.timedelta(days=1)
    while por_dia[d] > 0:
        atual += 1
        d -= dt.timedelta(days=1)
    recorde = corrida = 0
    d = hoje - dt.timedelta(days=371)
    while d <= hoje:
        corrida = corrida + 1 if por_dia[d] else 0
        recorde = max(recorde, corrida)
        d += dt.timedelta(days=1)
    return atual, recorde


def svg(D, t):
    W, H = 1000, 576
    hoje, por_dia = D["hoje"], D["por_dia"]
    # grade de 53 semanas terminando hoje (colunas começam no domingo)
    fim = hoje
    ini = fim - dt.timedelta(days=fim.isoweekday() % 7) - dt.timedelta(weeks=52)
    dias = [ini + dt.timedelta(days=i) for i in range((fim - ini).days + 1)]
    total = sum(por_dia[d] for d in dias)
    ativos = sum(1 for d in dias if por_dia[d])
    maxi = max([por_dia[d] for d in dias] + [1])
    def nivel(n):
        if n == 0: return 0
        f = n / maxi
        return 1 if f <= .15 else 2 if f <= .35 else 3 if f <= .65 else 4
    atual, recorde = sequencias(por_dia, hoje)

    o = []
    A = o.append
    A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Inter,Helvetica,Arial,sans-serif">')
    A("""<style>
@media (prefers-reduced-motion: no-preference){
 .c{opacity:0;animation:aparece .5s ease-out forwards}
 .b{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:cresce .7s cubic-bezier(.2,.8,.2,1) forwards}
 .h{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:abre .8s cubic-bezier(.2,.8,.2,1) forwards}
 .r{stroke-dasharray:0 999;animation:roda 1s ease-out forwards}
}
@keyframes aparece{to{opacity:1}} @keyframes cresce{to{transform:scaleY(1)}} @keyframes abre{to{transform:scaleX(1)}}
</style>""")
    A(f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>')
    # cabeçalho
    A(f'<text x="28" y="44" font-size="22" font-weight="700" fill="{t["fg"]}">Gusthavo Silva<tspan fill="{t["tint"]}">.</tspan></text>')
    A(f'<text x="28" y="64" font-size="13" fill="{t["mut"]}">Atividade no GitHub nos últimos 12 meses, repositórios privados incluídos</text>')
    A(f'<text x="{W-28}" y="44" font-size="12" fill="{t["mut"]}" text-anchor="end">atualizado em {hoje:%d/%m/%Y}</text>')

    # 1) mapa de calor
    cx, cy, cw, ch = 24, 84, W - 48, 214
    A(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="14" fill="{t["card"]}"/>')
    A(f'<text x="{cx+20}" y="{cy+30}" font-size="14" font-weight="600" fill="{t["fg"]}">Commits por dia</text>')
    A(f'<text x="{cx+cw-20}" y="{cy+30}" font-size="13" fill="{t["mut"]}" text-anchor="end">'
      f'<tspan fill="{t["fg"]}" font-weight="600">{br(total)}</tspan> commits · <tspan fill="{t["fg"]}" font-weight="600">{ativos}</tspan> dias com commit · '
      f'sequência atual <tspan fill="{t["tint"]}" font-weight="600">{atual} {"dia" if atual == 1 else "dias"}</tspan> · recorde {recorde}</text>')
    passo, cel = 16, 13
    x0, y0 = cx + 52, cy + 64
    ultimo_mes = None
    for i, d in enumerate(dias):
        col, lin = i // 7, d.isoweekday() % 7
        x, y = x0 + col * passo, y0 + lin * passo
        if lin == 0 and d.month != ultimo_mes and d.day <= 7:
            A(f'<text x="{x}" y="{y0-8}" font-size="11" fill="{t["mut"]}">{MESES[d.month-1]}</text>')
            ultimo_mes = d.month
        n = por_dia[d]
        tip = f'<title>{d:%d/%m/%Y}: {n} commit{"s" if n != 1 else ""}</title>'
        A(f'<rect class="c" style="animation-delay:{col*18}ms" x="{x}" y="{y}" width="{cel}" height="{cel}" rx="3" fill="{t["calor"][nivel(n)]}">{tip}</rect>')
    for lin, nome in ((1, "seg"), (3, "qua"), (5, "sex")):
        A(f'<text x="{cx+20}" y="{y0 + lin*passo + 10}" font-size="11" fill="{t["mut"]}">{nome}</text>')
    lx = cx + cw - 20 - 5 * 16 - 34
    A(f'<text x="{lx-8}" y="{cy+ch-14}" font-size="11" fill="{t["mut"]}" text-anchor="end">menos</text>')
    for k in range(5):
        A(f'<rect x="{lx + k*16}" y="{cy+ch-24}" width="12" height="12" rx="3" fill="{t["calor"][k]}"/>')
    A(f'<text x="{lx + 5*16 + 4}" y="{cy+ch-14}" font-size="11" fill="{t["mut"]}">mais</text>')

    # cartões de baixo
    by, bh, gap = cy + ch + 16, H - (cy + ch + 16) - 24, 16
    bw = (cw - 2 * gap) / 3
    def cartao(i, titulo):
        x = cx + i * (bw + gap)
        A(f'<rect x="{x:.1f}" y="{by}" width="{bw:.1f}" height="{bh}" rx="14" fill="{t["card"]}"/>')
        A(f'<text x="{x+20:.1f}" y="{by+30}" font-size="14" font-weight="600" fill="{t["fg"]}">{titulo}</text>')
        return x

    # 2) commits por mês
    x = cartao(0, "Commits por mês")
    meses = []
    m = dt.date(hoje.year, hoje.month, 1)
    for _ in range(12):
        meses.append(m)
        m = (m - dt.timedelta(days=1)).replace(day=1)
    meses.reverse()
    soma = {mm: sum(v for d, v in por_dia.items() if d.year == mm.year and d.month == mm.month) for mm in meses}
    mx = max(list(soma.values()) + [1])
    area_h, base = 118, by + bh - 34
    largura = (bw - 40) / 12
    for k, mm in enumerate(meses):
        v = soma[mm]
        hh = max(3, v / mx * area_h) if v else 3
        bx = x + 20 + k * largura + 3
        cor = t["tint"] if mm.month == hoje.month and mm.year == hoje.year else (t["calor"][3] if v == mx else t["calor"][2] if v else t["calor"][0])
        A(f'<rect class="b" style="animation-delay:{k*60}ms" x="{bx:.1f}" y="{base-hh:.1f}" width="{largura-6:.1f}" height="{hh:.1f}" rx="4" fill="{cor}"><title>{MESES[mm.month-1]}/{mm.year}: {v} commits</title></rect>')
        A(f'<text x="{bx + (largura-6)/2:.1f}" y="{base+18}" font-size="10" fill="{t["mut"]}" text-anchor="middle">{MESES[mm.month-1][0].upper()}</text>')
        if v == mx or k == 11:
            A(f'<text x="{bx + (largura-6)/2:.1f}" y="{base-hh-6:.1f}" font-size="11" font-weight="600" fill="{t["fg"]}" text-anchor="middle">{v}</text>')

    # 3) linguagens (rosca)
    x = cartao(1, "Linguagens nos projetos")
    top = D["linguas"].most_common(5)
    resto = sum(D["linguas"].values()) - sum(v for _, v in top)
    fatias = top + ([("Outras", resto)] if resto / (sum(D["linguas"].values()) or 1) >= .005 else [])
    tot = sum(v for _, v in fatias) or 1
    rx, ry, raio, esp = x + 78, by + 130, 52, 20
    circ = 2 * 3.14159265 * raio
    A(f'<circle cx="{rx:.1f}" cy="{ry}" r="{raio}" fill="none" stroke="{t["calor"][0]}" stroke-width="{esp}"/>')
    acum = 0
    for k, (nome, v) in enumerate(fatias):
        cor = D["cores"].get(nome, t["mut"])
        L = v / tot * circ
        A(f'<circle class="r" style="animation-delay:{k*120}ms;stroke-dasharray:{L:.1f} {circ:.1f}" cx="{rx:.1f}" cy="{ry}" r="{raio}" fill="none" stroke="{cor}" stroke-width="{esp}" '
          f'stroke-dashoffset="{-acum:.1f}" transform="rotate(-90 {rx:.1f} {ry})"><title>{nome}: {v/tot:.0%}</title></circle>')
        acum += L
    A(f'<text x="{rx:.1f}" y="{ry+5}" font-size="15" font-weight="700" fill="{t["fg"]}" text-anchor="middle">{len(D["linguas"])}</text>')
    A(f'<text x="{rx:.1f}" y="{ry+20}" font-size="9" fill="{t["mut"]}" text-anchor="middle">linguagens</text>')
    lx, ly = x + 158, by + 66
    for k, (nome, v) in enumerate(fatias):
        cor = D["cores"].get(nome, t["mut"])
        yy = ly + k * 24
        A(f'<circle cx="{lx}" cy="{yy-4}" r="5" fill="{cor}"/>')
        A(f'<text x="{lx+12}" y="{yy}" font-size="12" fill="{t["fg"]}">{nome}</text>')
        A(f'<text x="{x+bw-20:.1f}" y="{yy}" font-size="12" fill="{t["mut"]}" text-anchor="end">{"<1%" if v/tot < .005 else f"{v/tot:.0%}"}</text>')

    # 4) repositórios
    x = cartao(2, "Repositórios")
    pub, pri = D["repos"] - D["privados"], D["privados"]
    A(f'<text x="{x+20:.1f}" y="{by+78}" font-size="38" font-weight="700" fill="{t["fg"]}">{D["repos"]}</text>')
    A(f'<text x="{x+20+24*len(str(D["repos"])):.1f}" y="{by+78}" font-size="12" fill="{t["mut"]}">{pub} públicos · {pri} privados</text>')
    bx, bwid, byy = x + 20, bw - 40, by + 94
    A(f'<rect x="{bx:.1f}" y="{byy}" width="{bwid:.1f}" height="10" rx="5" fill="{t["calor"][0]}"/>')
    if D["repos"]:
        A(f'<rect class="h" x="{bx:.1f}" y="{byy}" width="{bwid*pub/D["repos"]:.1f}" height="10" rx="5" fill="{t["tint"]}"/>')
    A(f'<text x="{x+20:.1f}" y="{by+136}" font-size="11" fill="{t["mut"]}">Públicos mexidos por último</text>')
    for k, (nome, cor) in enumerate(D["recentes"]):
        yy = by + 154 + k * 21
        A(f'<circle cx="{x+26:.1f}" cy="{yy-4}" r="5" fill="{cor}"/>')
        A(f'<text x="{x+38:.1f}" y="{yy}" font-size="12" fill="{t["fg"]}">{nome}</text>')
    A(f'<text x="{x+20:.1f}" y="{by+bh-14}" font-size="12" fill="{t["mut"]}">'
      f'<tspan fill="{t["tint"]}">★</tspan> {D["estrelas"]} estrelas · {D["seguidores"]} seguidores</text>')
    A("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    D = coletar()
    for nome, t in TEMAS.items():
        (AQUI / f"{nome}.svg").write_text(svg(D, t), encoding="utf-8")
    print("ok", sum(D["por_dia"].values()), "commits")
