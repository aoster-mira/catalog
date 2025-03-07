import yaml
from collections import defaultdict
import argparse
from jinja2 import Template

mcs_tpl = """
apiVersion: k0rdent.mirantis.com/v1alpha1
kind: MultiClusterService
metadata:
  name: {{ app }}
spec:
  clusterSelector:
    matchLabels:
      group: demo
  serviceSpec:
    services:
    {{ services | replace("\n", "\n    ") }}
"""

class ValuesClass:
    """Dump service values string using | notation"""

    def __init__(self, lines: list):
        self.s = ("\n".join(lines)).strip() + "\n"


def representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data.s, style="|")


yaml.add_representer(ValuesClass, representer)


def get_service_template(name: str, version: str) -> str:
    template_version = str.replace(version, '.', '-')
    return f"{name}-{template_version}"


def get_mcs_services(chart_data: dict, chart_values_data):
    deps = chart_data['dependencies']
    services = []
    ns = deps[0]['name'] # use a common namespace
    for dep in deps:
        dep_name = dep['name']
        service = dict(
            template = get_service_template(dep_name, dep['version']),
            name = dep_name,
            namespace = ns
        )
        if dep_name in chart_values_data:
            service['values'] = ValuesClass(chart_values_data[dep_name])
        services.append(service)
    return yaml.dump(services, sort_keys=False, default_flow_style=False)


def render_mcs_template(app: str):
    template = Template(mcs_tpl)
    chart_data = get_chart_data(app)
    chart_values_data = get_chart_values_data(app)
    mcs_services = get_mcs_services(chart_data, chart_values_data)
    data = {"app": app, "services": mcs_services}
    rendered = template.render(data).strip() + "\n"
    return rendered


def render_mcs(args):
    app = args.app
    output = render_mcs_template(app)
    print(output)
    with open(f"apps/{app}/mcs.yaml", "w", encoding='utf-8') as file:
        file.write(output)


def get_install_cmd(release: str, repo: str, prefix: str | None, charts: list) -> str:
    cmd_lines = []
    cmd_lines.append(f'helm upgrade --install {release} oci://ghcr.io/k0rdent/catalog/charts/kgst -n kcm-system')
    cmd_lines.append(f'    --set "helm.repository.url={repo}"')
    if prefix:
        cmd_lines.append(f'    --set "prefix={prefix}"')

    for i, chart in enumerate(charts):
        cmd_lines.append(f'    --set "helm.charts[{i}].name={chart['name']}"')
        cmd_lines.append(f'    --set "helm.charts[{i}].version={chart['version']}"')

    cmd = " \\\n".join(cmd_lines)
    return cmd


def show_install_cmd(args: str):
    app = args.app
    helm_config_path = f"apps/{app}/helm-values-kgst.yaml"
    helm_config = None
    with open(helm_config_path, "r", encoding='utf-8') as file:
        helm_config = yaml.safe_load(file)

    repo = helm_config['helm']['repository']['url']
    prefix = helm_config.get('prefix')
    charts = helm_config['helm']['charts']
    cmd = get_install_cmd(repo, prefix, charts)
    print(cmd)


def get_chart_data(app: str) -> dict:
    chart_path = f"apps/{app}/example/Chart.yaml"
    with open(chart_path, "r", encoding='utf-8') as file:
        chart = yaml.safe_load(file)
        return chart


def get_chart_values_data(app: str) -> dict:
    chart_values_path = f"apps/{app}/example/values.yaml"
    with open(chart_values_path, "r", encoding='utf-8') as file:
        deps = [dep for dep in yaml.safe_load(file)]
        file.seek(0)
        dep = ""
        i_next = 0
        values_lines = dict()
        for line in file.read().split('\n'):
            if len(deps) > i_next and str.startswith(line, f"{deps[i_next]}:"):
                dep = deps[i_next]
                values_lines[dep] = []
                i_next += 1
            else:
                values_lines[dep].append(line)
        return values_lines


def chart_2_repos(chart: dict) -> dict:
    """Get unique repos from chart deps"""
    
    repos = defaultdict(list)
    for dep in chart['dependencies']:
        repos[dep['repository']].append(dep)

    return repos


def kgst_install_deps(args):
    app = args.app
    chart = get_chart_data(app)
    repos = chart_2_repos(chart)
    for repo in repos:
        charts = repos[repo]
        release = charts[0]['name']
        cmd = get_install_cmd(release, repo, None, charts)
        print(cmd)


parser = argparse.ArgumentParser(description='Catalog dev tool.',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)  # To show default values in help.
subparsers = parser.add_subparsers(dest="command", required=True)

show = subparsers.add_parser("show-install-cmd", help="Show 'kgst' install command")
show.add_argument("app")
show.set_defaults(func=show_install_cmd)

install = subparsers.add_parser("kgst-install-deps", help="Install example chart deps using 'kgst'")
install.add_argument("app")
install.set_defaults(func=kgst_install_deps)

install = subparsers.add_parser("render-mcs", help="Render MultiClusterService using app example chart")
install.add_argument("app")
install.set_defaults(func=render_mcs)

args = parser.parse_args()
args.func(args)
