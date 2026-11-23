#!/usr/bin/env python3
import argparse
import os
import socket
import tempfile

CHUNK_SIZE = 0x10000
PAGE_SIZE = 0x1000

parser = argparse.ArgumentParser(description="Dump guest memory through the QEMU HMP monitor socket.")
parser.add_argument("--monitor", required=True, help="unix socket given to --qemu-monitor unix:PATH,server,nowait")
parser.add_argument("--out", required=True, help="output directory")
parser.add_argument("--prefix", required=True, help="file name prefix, for example EL71v45")
parser.add_argument("--keep-stopped", action="store_true", help="leave the guest stopped after the dump")
parser.add_argument("regions", nargs="+", help="NAME:START:SIZE in hex, ':virt' reads through the MMU, for example VMALLOC:AC000000:01800000:virt")
args = parser.parse_args()


class Monitor:
	def __init__(self, path):
		self.sock = socket.socket(socket.AF_UNIX)
		self.sock.connect(path)
		self.sock.settimeout(120)
		self.read_reply()

	def read_reply(self):
		data = b""
		while not data.endswith(b"(qemu) "):
			chunk = self.sock.recv(65536)
			if not chunk:
				raise RuntimeError("monitor closed the connection")
			data += chunk
		return data.decode(errors="replace")

	def execute(self, command):
		self.sock.sendall(command.encode() + b"\n")
		reply = self.read_reply()
		if "Error" in reply or "Invalid" in reply:
			raise RuntimeError(f"{command}: {reply.strip()}")


def dump_physical(monitor, start, size, path):
	monitor.execute(f'pmemsave 0x{start:X} 0x{size:X} "{path}"')


def read_virtual(monitor, start, size, scratch):
	try:
		monitor.execute(f'memsave 0x{start:X} 0x{size:X} "{scratch}"')
	except RuntimeError:
		return None
	with open(scratch, "rb") as file:
		return file.read()


def dump_virtual(monitor, start, size, path):
	mapped = 0
	with tempfile.NamedTemporaryFile(dir=args.out, suffix=".tmp") as scratch, open(path, "wb") as output:
		for chunk in range(start, start + size, CHUNK_SIZE):
			data = read_virtual(monitor, chunk, CHUNK_SIZE, scratch.name)
			if data is not None:
				output.write(data)
				mapped += CHUNK_SIZE
				continue
			for page in range(chunk, chunk + CHUNK_SIZE, PAGE_SIZE):
				data = read_virtual(monitor, page, PAGE_SIZE, scratch.name)
				if data is not None:
					mapped += PAGE_SIZE
				output.write(data if data is not None else bytes(PAGE_SIZE))
	return mapped


os.makedirs(args.out, exist_ok=True)
monitor = Monitor(args.monitor)
monitor.execute("stop")
for region in args.regions:
	fields = region.split(":")
	name = fields[0]
	start = int(fields[1], 16)
	size = int(fields[2], 16)
	path = os.path.abspath(os.path.join(args.out, f"{args.prefix}_{name}_{start:08X}_{size:08X}.bin"))
	if fields[3:] == ["virt"]:
		mapped = dump_virtual(monitor, start, size, path)
		print(f"{path}: {mapped:#x} of {size:#x} bytes mapped, unmapped pages are zero")
	else:
		dump_physical(monitor, start, size, path)
		print(path)
if not args.keep_stopped:
	monitor.execute("cont")
