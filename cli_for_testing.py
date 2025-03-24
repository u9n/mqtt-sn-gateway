import os
import click
import socket
import time

@click.group()
@click.option('--host',  help='Target host for MQTT-SN gateway')
@click.option('--port', default=1884, help='Target port for MQTT-SN gateway')
@click.option('--bind-port', default=33000, help='Local port to bind to')
@click.pass_context
def cli(ctx, host, port, bind_port):
    """MQTT-SN example scripts CLI"""
    ctx.ensure_object(dict)
    ctx.obj['host'] = host
    ctx.obj['port'] = port
    ctx.obj['bind_port'] = bind_port

@cli.command()
@click.pass_obj
def connect(ctx):
    """Send a CONNECT message to the MQTT-SN gateway"""
    msg = b'\x16\x04\x04\x01\xfd 94193A04010020B8'
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("localhost", ctx["bind_port"]))
    click.echo(f"Sending CONNECT message to {ctx['host']}:{ctx['port']}")
    s.sendto(msg, (ctx['host'], ctx['port']))
    click.echo("Message sent")

@cli.command()
@click.pass_obj
def publish(ctx):
    """Send a PUBLISH message to the MQTT-SN gateway"""
    msg = b'\xa2\x0c\xa0\x00\x01\xc7\x92{"TS":"2021-07-05T18:00:00Z","ID":224396,"E":184,"U":"kWh","V":6580,"VU":"l","P":0,"PU":"W","F":0,"FU":"l/h","FT":0,"TU":"C","RT":0,"RU":"C","EF":"0x0421"}'
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("localhost", ctx["bind_port"]))
    click.echo(f"Sending PUBLISH message to {ctx['host']}:{ctx['port']}")
    s.sendto(msg, (ctx['host'], ctx['port']))
    click.echo("Message sent")

@cli.command()
@click.option('--topic-name', default='mr/94193A04010020B8/standard/json', help='Topic name to register')
@click.pass_obj
def register(ctx, topic_name):
    """Send a REGISTER message to the MQTT-SN gateway"""
    # Convert hex msg_id to bytes
    msg_id_bytes = os.urandom(2)
    
    # Construct the REGISTER message
    # Format: length(1) + msg_type(1) + topic_id(2) + msg_id(2) + topic_name
    msg = b"'\n\x00\x00" + msg_id_bytes + topic_name.encode()
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("localhost", ctx["bind_port"]))
    click.echo(f"Sending REGISTER message to {ctx['host']}:{ctx['port']}")
    click.echo(f"Topic name: {topic_name}")
    click.echo(f"Message ID: {msg_id_bytes}")
    s.sendto(msg, (ctx['host'], ctx['port']))
    click.echo("Message sent")

if __name__ == '__main__':
    cli() 