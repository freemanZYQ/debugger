#!/usr/bin/env python3

import re
import socket
from struct import pack, unpack
from binascii import hexlify, unhexlify

from . import rsp
from . import gdblike
from . import DebugAdapter

linux_signal_to_name = {
	# ISO C99
	2: 'SIGINT',
	4: 'SIGILL',
	6: 'SIGABRT',
	8: 'SIGFPE',
	11: 'SIGSEGV',
	15: 'SIGTERM',

	# historical POSIX
	1: 'SIGHUP',
	3: 'SIGQUIT',
	5: 'SIGTRAP',
	9: 'SIGKILL',
	10: 'SIGUSR1',	# differs from macos
	12: 'SIGUSR2',	# differs from macos
	13: 'SIGPIPE',
	14: 'SIGALRM',

	# newer POSIX
	16: 'SIGSTKFLT',
	17: 'SIGCHLD',	# differs from macos
	18: 'SIGCONT',	# differs from macos
	19: 'SIGSTOP',	# differs
	20: 'SIGTSTP',	# differs
	21: 'SIGTTIN',
	22: 'SIGTTOU',
	23: 'SIGURG', # differs from macos
	24: 'SIGXCPU',
	25: 'SIGXFSZ',
	26: 'SIGVTALRM',
	27: 'SIGPROF',
	30: 'SIGUSR1',
	31: 'SIGUSR2',

	# nonstandard POSIX
	28: 'SIGWINCH',

	# unallocated posix
	7: 'SIGBUX',	# differs from macos
	29: 'SIGPOLL',

	30: 'SIGSTKFLT',
	31: 'SIGSYS'
}

linux_signal_to_debugadapter_reason = {
	1: DebugAdapter.STOP_REASON.SIGNAL_HUP,
	2: DebugAdapter.STOP_REASON.SIGNAL_INT,
	4: DebugAdapter.STOP_REASON.SIGNAL_ILL,
	6: DebugAdapter.STOP_REASON.SIGNAL_ABRT,
	8: DebugAdapter.STOP_REASON.SIGNAL_FPE,
	11: DebugAdapter.STOP_REASON.SIGNAL_SEGV,
	15: DebugAdapter.STOP_REASON.SIGNAL_TERM,
	3: DebugAdapter.STOP_REASON.SIGNAL_QUIT,
	5: DebugAdapter.STOP_REASON.SIGNAL_TRAP,
	9: DebugAdapter.STOP_REASON.SIGNAL_KILL,
	10: DebugAdapter.STOP_REASON.SIGNAL_USR1,
	12: DebugAdapter.STOP_REASON.SIGNAL_USR2,
	13: DebugAdapter.STOP_REASON.SIGNAL_PIPE,
	14: DebugAdapter.STOP_REASON.SIGNAL_ALRM,
	16: DebugAdapter.STOP_REASON.SIGNAL_STKFLT,
	17: DebugAdapter.STOP_REASON.SIGNAL_CHLD,
	18: DebugAdapter.STOP_REASON.SIGNAL_CONT,
	19: DebugAdapter.STOP_REASON.SIGNAL_STOP,
	20: DebugAdapter.STOP_REASON.SIGNAL_TSTP,
	21: DebugAdapter.STOP_REASON.SIGNAL_TTIN,
	22: DebugAdapter.STOP_REASON.SIGNAL_TTOU,
	23: DebugAdapter.STOP_REASON.SIGNAL_URG,
	24: DebugAdapter.STOP_REASON.SIGNAL_XCPU,
	25: DebugAdapter.STOP_REASON.SIGNAL_XFSZ,
	26: DebugAdapter.STOP_REASON.SIGNAL_VTALRM,
	27: DebugAdapter.STOP_REASON.SIGNAL_PROF,
	30: DebugAdapter.STOP_REASON.SIGNAL_USR1,
	31: DebugAdapter.STOP_REASON.SIGNAL_USR2,
	28: DebugAdapter.STOP_REASON.SIGNAL_WINCH,
	7: DebugAdapter.STOP_REASON.SIGNAL_BUX,
	29: DebugAdapter.STOP_REASON.SIGNAL_POLL,
	30: DebugAdapter.STOP_REASON.SIGNAL_STKFLT,
	31: DebugAdapter.STOP_REASON.SIGNAL_SYS
}

# asynchronously called when inside a "go" to inform us of stdout (and
# possibly other stuff)
def handler_async_pkt(pkt):
	if pkt.startswith('O'):
		msg = pkt[1:]
		print(''.join([chr(int(msg[2*x:2*x+2], 16)) for x in range(int(len(msg)/2))]), end='')
	else:
		print('handler_async_pkt() got unknown packet: %s' % repr(pkt))

class DebugAdapterGdb(gdblike.DebugAdapterGdbLike):
	def __init__(self, **kwargs):
		gdblike.DebugAdapterGdbLike.__init__(self, **kwargs)

		# in gdb, do a dance so commands like qXfer will work
		rsp.tx_rx(self.sock, 'Hg0')
		# if 'multiprocess+' in list here, thread reply is like 'pX.Y' where X is core id, Y is thread id
		rsp.tx_rx(self.sock, 'qSupported:swbreak+;hwbreak+;qRelocInsn+;fork-events+;vfork-events+;exec-events+;vContSupported+;QThreadEvents+;no-resumed+;xmlRegisters=i386')
		self.reg_info_load()

	#--------------------------------------------------------------------------
	# API
	#--------------------------------------------------------------------------

	#--------------------------------------------------------------------------
	# helpers, NOT part of the API
	#--------------------------------------------------------------------------

	# returns (STOP_REASON.XXX, <extra_info>)
	def go_generic(self, gotype, handler_async_pkt=None):
		try:
			reply = rsp.tx_rx(self.sock, gotype, 'mixed_output_ack_then_reply', handler_async_pkt)
			(reason, reason_data) = (None, None)

			# thread info
			if reply[0] == 'T':
				tdict = rsp.packet_T_to_dict(reply)
				self.active_thread_tid = tdict['thread']
				signum = tdict.get('signal', 0)
				(reason, reason_data) = \
					(linux_signal_to_debugadapter_reason.get(signum, DebugAdapter.STOP_REASON.UNKNOWN), signum)

			# exit status
			elif reply[0] == 'W':
				exit_status = int(reply[1:], 16)
				print('inferior exited with status: %d' % exit_status)
				(reason, reason_data) = (DebugAdapter.STOP_REASON.PROCESS_EXITED, exit_status)

			else:
				print(reply)
				(reason, reason_data) = (DebugAdapter.STOP_REASON.UNKNOWN, None)

			return (reason, reason_data)

		except rsp.RspDisconnected:
			return (DebugAdapter.BACKEND_DISCONNECTED, None)

	def raw(self, data):
		return rsp.tx_rx(self.sock, data)
