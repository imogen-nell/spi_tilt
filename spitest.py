import time
import spidev
import RPi.GPIO as GPIO
#######

CS_TILT 		= 18 #pin12 is BCM 18

SW_RESET	    = [0xB4, 0x00, 0x20, 0x98]
WHOAMI  	    = [0x40, 0x00, 0x00, 0x91]
READ_STAT 		= [0x18, 0x00, 0x00, 0xE5]
MODE_1   		= [0xB4, 0x00, 0x00, 0x1F]
READ_CMD  		= [0x34, 0x00, 0x00, 0xDF]
WAKE_UP   		= [0xB4, 0x00, 0x00, 0x1F]
ANG_CTRL  		= [0xB0, 0x00, 0x1F, 0x6F]
READ_CURR_BANK  = [0x7C, 0X00, 0X00, 0XB3]
SW_TO_BNK0		= [0xFC, 0x00, 0x00, 0x73]
ANG_X			= [0x24, 0x00, 0x00, 0xC7]
ANG_Y			= [0x28, 0x00, 0x00, 0xCD]
ANG_Z			= [0x2C, 0x00, 0x00, 0xCB]

#######
# Enable SPI
bus = 1
device = 0
spi = spidev.SpiDev()
spi.open(bus, device)
spi.max_speed_hz = 2000000 #2-4 MHz
spi.mode = 0 # from data sheet
GPIO.setwarnings(False)
#set chip select pin to output & high
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_TILT, GPIO.OUT)
GPIO.output(CS_TILT, 1) 
time.sleep(0.05)
##############

#Write bytes to the SPI device
# arg : data - list of bytes to write eg ['0x00', '0x00', '0x00', '0x00']
def write(data):
	GPIO.output(CS_TILT, 0) 
	spi.writebytes(data)
	time.sleep(0.02) # must give it at leat 10ms to process
	GPIO.output(CS_TILT, 1)
	time.sleep(0.015)
	return

#Read bytes from the SPI device
# arg : bytecount - number of bytes to read eg 4
# return : list of bytes read
def read(bytecount):
	GPIO.output(CS_TILT, 0)
	ret = spi.readbytes(bytecount)
	time.sleep(0.02)
	GPIO.output(CS_TILT, 1)
	time.sleep(0.015)
	return ret

#preforms wirte and read, the read will 
#be responce to previous request as per the protocol
# arg : request - list of bytes to write eg ['0x00', '0x00', '0x00', '0x00']
# arg : bytecount - number of bytes to read eg 4
# return : list of bytes read
def frame(request, bytecount=4):
	GPIO.output(CS_TILT, 0)
	spi.writebytes(request)
	responce = spi.readbytes(bytecount)
	time.sleep(0.04)
	GPIO.output(CS_TILT, 1)
	time.sleep(0.005)
	return responce

#writes then Reads bytes from the SPI device
#writes and read in separate frames/transactions
# arg : msg - list of bytes to write eg ['0x00', '0x00', '0x00', '0x00']
# arg : nbytes - number of bytes to read eg 4
# return : list of bytes read
def xfer(msg, nbytes=0):
	if nbytes == 0: nbytes = len(msg)
	#request
	write(msg)
	#response
	ret = read(nbytes)
	return ret

##start up sequence 
##do once at begining of the program
#something is wrong if the checksums are not correct
def read_start_up():
	print("*****(read) start up sequence *****")
	GPIO.output(CS_TILT, 1)
	#request 1 
	write(SW_TO_BNK0)
	#garbage = read(4)
	#request 2 & responce to 1
	resp1 = frame(SW_RESET)
	#request 3 SET MEASUREMENT MODE
	resp2 = frame(MODE_1)
	#request 4 write ANG_CTRL to enable angle outputs
	resp3 = frame(ANG_CTRL)
	#request 5 clear and read STATUS 
	resp4 = frame(READ_STAT)
	#responce to request 5 
	status  = read(4)

	#print("status (dec):", status)
	print("status:", toHex(status))

	print("SW TO BNK 0 :", toHex(resp1))
	if(hex(resp1[3])!=calculate_crc(resp1) ):
		print("checksum error resp1")
	print("SW RESET    :", toHex(resp2))
	if(hex(resp2[3])!=calculate_crc(resp2) ):
		print("checksum error resp2")
	print("MODE 1      :", toHex(resp3))
	if(hex(resp3[3])!=calculate_crc(resp3) ):
		print("checksum error resp3")
	print("ANG CTRL    :", toHex(resp4))
	if(hex(resp4[3])!=calculate_crc(resp4) ):
		print("checksum error resp4")
	print("READ STAT   :", toHex(status))
	if(hex(status[3])!=calculate_crc(status) ):
		print("checksum error status")
	time.sleep(0.025)
	print("*****start up sequence complete*****")

#calcuates crc for the given data
# arg : data - list of bytes to calculate crc eg ['0x00', '0x00', '0x00', '0x00']
# return : crc as hex, should match the last byte of the data else error
def calculate_crc(data):
	data = toHex(data)
	data = toLongDec(data)
	CRC = 0xFF
	for BitIndex in range(31, 7, -1):
		BitValue = (data >> BitIndex) & 0x01
		CRC = crc8(BitValue, CRC)
	CRC = ~CRC & 0xFF
	return hex(CRC)

##used i  calculate_crc
def crc8(BitValue, CRC):
    Temp = CRC & 0x80
    if BitValue == 0x01:
        Temp ^= 0x80
    CRC <<= 1
    if Temp > 0:
        CRC ^= 0x1D
    return CRC

#read response as HEX
def toHex(msg):
	return [hex(num) for num in msg]

#converts hex data to angle
# arg : output bytes of excecute_command(ANG_XYZ) (hex)
# return : angle in degrees to 2 decimal places
def convertToAngle(hex):
  dec = hextodec(hex)
  return round((dec / 2**14)*90, 2)

#converts hex to decimal
# arg : hex - hex string eg '0x00'
# return : decimal value
def hextodec(hex):
  hexes = {'a': 10, 'b': 11, 'c': 12,'d': 13, 'e': 14, 'f': 15, 'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15}
  dec = 0
  i=-1
  x=0
  while hex[i]!='x':
    # print(hex[i], i)
    if hex[i] in hexes:
      dec+= 16**x * hexes[hex[i]]
    else:
      dec += 16**x * int(hex[i])
    i-=1
    x+=1
  return dec

#convert hex list to one string 
##eg [0x44, 0x55, 0x66] -> 0x445566 --> dec(0x445566) = 4479778 etc.
def toLongDec(hex_list):
	lst = [int(hex_str, 16) for hex_str in hex_list]
	return int('0x' + ''.join(hex(num)[2:].zfill(2) for num in lst),16)

#convert hex list to one string 
##eg [0x44, 0x55, 0x66] -> 0x445566
def toLongHex(hex_list):
  str =''
  for hex_str in hex_list:
    tempstr=''
    i=-1
    x=0
    while hex_str[i] !='x':
      tempstr+=(hex_str[i])
      i-=1
      x+=1
    str += tempstr[::-1]
  return ('0x' + str)
#Read the WHOAMI register, built in init request (run at start)
# return : WHOAMI register value, expect data to be 0x00C1 always 
def whoami():
    GPIO.output(CS_TILT, 0)
    time.sleep(0.001)
	#discard first read
    dummy_32 = xfer(WHOAMI)  # Ask who am I
    time.sleep(0.01)

    whoami_register = xfer( WHOAMI)  # Ask again
    time.sleep(0.01)

    GPIO.output(CS_TILT, 1)

    return whoami_register

#converts hex to binary, used in get_OP()
#arg : num - hex string eg '0x00'
#return : binary string
def getbin(num):
	num = bin(int(num, 16))[2:]
	while len(num)<8:
		num = '0'+str(num)  
	return num

#separated the OP code into RW, ADDR, RS and prints them on the screen
#used by excecute_command()
#arg : data - 8 bit / 1 byte hex string eg '0xC1'
#2 lsb - RW, next 5 bits - ADDR, last 1 bit - RS
def get_OP(data):
	num = getbin(data)
	print("RW:", num[0])
	print("ADDR:", hex(int(num[1:6],2)))
	print("RS:", num[6:])
	return

#excecutes the command and prints the responce
#arg : command - list of 4 bytes to write eg ['0x00', '0x00', '0x00', '0x00']
#arg : key - string to print the command name eg 'WHOAMI'
def excecute_command(command, key):
	write(command)
	i = frame(command)
	if hex(i[3])!=calculate_crc(i):
		print("checksum error")
		return
	elif 'ANG' in key:
		i = toHex(i)
		print("\n*************************\n")
		print(key + " responce:")
		get_OP(i[0])
		print("angle:", convertToAngle(toLongHex(i[1:3])))
		print("\n*************************\n")
	else:
		i = toHex(i)
		print("\n*************************\n")
		print(key + " responce:")
		get_OP(i[0])
		print("data:", toLongHex(i[1:3]))
		print("\n*************************\n")
	return
#excecutes the command and returns the angle read
#arg : read angle command. allowed commands are ANG_X, ANG_Y, ANG_Z
def excecute_angle(command, key):
	write(command)
	i = frame(command)
	if not ('ANG_' in key):
		print("invalid command")
		return
	elif hex(i[3])!=calculate_crc(i):
		print("checksum error")
		return
	i = toHex(i)
	hexnum = toLongHex(i[1:3])
	print("data:", hexnum)
	angle = convertToAngle(hexnum)
	print("angle:", angle)
	signedAngle = round((twosCompMag(hexnum)/ 2**14)*90, 2)
	if signedAngle == angle:
		print("signed angle:", signedAngle, "-->", signedAngle-180)
	else:
		print("signed angle:", signedAngle)
	return angle  

def twosCompMag(num):
	positive = sign(num)
	if positive:
		return int(num,16)
	return twoshextoDec(num)
  
def sign(num):
	bins = bin(int(num, 16))[2:]
	if bins[0]=='0' or len(bins)<16:
		return True
	return False

def twoshextoDec(hex):
	dec = int(hex, 16)
	bins = bin(dec)[2:]
	ones = ''.join('1' if bit == '0' else '0' for bit in bins)
	twos = int(ones,2)+1
	return twos

##main
try: 	
	read_start_up()
	time.sleep(1)
	write(WHOAMI)
	while True:
		excecute_angle(ANG_X, 'ANG_X')
		# print("*"*20)
		#print("angle:" , excecute_angle(ANG_X, 'ANG_X'))
		#print("y:" , excecute_angle(ANG_Y, 'ANG_Y'))
		#print("z:" , excecute_angle(ANG_Z, 'ANG_Z'))
		print("*"*20)
		time.sleep(1)
	
except KeyboardInterrupt:
	spi.close()
