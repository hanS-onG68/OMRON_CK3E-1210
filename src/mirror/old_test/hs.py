import click

@click.group()
def cli():
    pass

@cli.command()
@click.argument("host")
@click.option("--port", default=8000, help="监听端口")
def start(host, port):
    """启动服务"""
    click.echo(f"Starting server at {host}:{port}")

@cli.command()
@click.argument("pid", type=int)
def stop(pid):
    """停止服务"""
    click.echo(f"Stopping process {pid}")



if __name__ == "__main__":
    import numpy as np
    lis = [[1, 2],[3, 4]]
    arr = np.asarray(lis)
    print(arr)
