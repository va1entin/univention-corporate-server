/*
 * Univention Client Login
 *  this file is part of the Univention thin client tools
 *
 * Copyright 2004-2010 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */

#ifndef _NEW_PROTOCOL_H_
#define _NEW_PROTOCOL_H_

#include "bits/types.h"

//typedef uint16_t protocol_command_t;
//typedef uint32_t protocol_length_t;
typedef unsigned short int protocol_command_t;
typedef unsigned int protocol_length_t;

#define COMMAND_ACK		0x01
#define COMMAND_ALIVE		0x02
#define COMMAND_ERROR           0x03

#define COMMAND_EXEC		0x11
#define COMMAND_START           0x12

#define COMMAND_FD_OPEN		0x21
#define COMMAND_FD_CLOSE	0x22
#define COMMAND_FD_DATA		0x23

#define COMMAND_SETTING_GET	0x31
#define COMMAND_SETTING_SET	0x32
#define COMMAND_SETTING_SETENV  0x33
#define COMMAND_SETTING_UNSETENV 0x34

#define COMMAND_RED_STDOUT      0x51
#define COMMAND_RED_STDERR      0x52

#define COMMAND_END_EXIT        0x61
#define COMMAND_END_WAITCHILD   0x62
#define COMMAND_END_CLEANUP     0x63

#define COMMAND_MOUNT           0x71

#define MAX_CMD_LEN             4096
#define MAX_CMD_ARGS            4096

// This PDU data structure is sent "on the wire". It specifies the length
// of the argument and data header.
struct raw_message_t {
  protocol_command_t command;
  protocol_length_t args_length;
  protocol_length_t data_length;
};

/* used in the interface */
struct message {
  protocol_command_t command;
  protocol_length_t args_length;
  protocol_length_t data_length;
  void* args;
  void* data;
};

int protocol_send_message_fd(int recv_fd, int send_fd, struct message* message);
int protocol_recv_message_fd(int recv_fd, int send_fd, struct message* message);
int protocol_send_message(struct message* message);
int protocol_recv_message(struct message* message);
int protocol_send_ack_fd(int recv_fd, int send_fd);
int protocol_recv_ack_fd(int recv_fd, int send_fd);


#endif /* _NEW_PROTOCOL_H_ */
