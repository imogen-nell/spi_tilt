import time
import spidev
import RPi.GPIO as GPIO

#######
SW_RESET	    = [0xB4, 0x00, 0x20, 0x98]
WHOAMI  	    = [0x40, 0x00, 0x00, 0x91]
CS_TILT 		=  18 
SPI_TILT 		= 0 ##TODO wtf is this 
READ_STAT 		= [0x18, 0x00, 0x00, 0xE5]
MODE_1   		= [0xB4, 0x00, 0x00, 0x1F]
READ_CMD  		= [0x34, 0x00, 0x00, 0xDF]
WAKE_UP   		= [0xB4, 0x00, 0x00, 0x1F]
ANG_CTRL  		= [0xB0, 0x00, 0x1F, 0x6F]
READ_CURR_BANK  = [0x7C, 0X00, 0X00, 0XB3]
SW_TO_BNK0		= [0xFC, 0x00, 0x00, 0x73]
READ_BANK_LSB   = [0xB3, 0X00, 0X00, 0X7C]

#######
bus = 1
device = 0
# Enable SPI #
spi = spidev.SpiDev()
spi.open(bus, device)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CS_TILT, GPIO.OUT)
#begin with CS high
GPIO.output(CS_TILT, 1) 
spi.max_speed_hz = 2000000 #2-4 MHz
spi.mode = 0
time.sleep(0.0005)
##############

def write(data):

	GPIO.output(CS_TILT, 0) #pin12 is BCM 18
	spi.write(data)
	GPIO.output(CS_TILT, 1)
	time.sleep(0.05)

def read(data, nbytes):
	msg = bytearray()
	msg.append(data)
	GPIO.output(CS_TILT, 0)
	spi.write(msg)
	print("msg:", msg)
	ret = spi.read(nbytes)
	GPIO.output(CS_TILT, 1)
	return ret

def xfer(data):
	GPIO.output(CS_TILT, 0)
	time.sleep(0.01)
	ret = spi.xfer(CS_TILT, data) ##added first arg
	time.sleep(0.02)
	GPIO.output(CS_TILT, 1)
	time.sleep(.01)

	return ret

def start_up():
	print("*****start up sequence *****")
	GPIO.output(CS_TILT, 1)
	xfer(SW_TO_BNK0)
	#wake up from power down 
	xfer(SW_RESET)
	#SET MEASUREMENT MODE
	xfer(MODE_1)
	#write ANG_CTRL to enable angl outputs
	xfer(ANG_CTRL)
	#clear status
	#read STATUS 
	dummyread0 = xfer(READ_STAT)
	dummyread1 = xfer([0x00])
	status = xfer(READ_STAT)

	print("status:", status)
	print("read0:", dummyread0)
	print("read1:", dummyread1)
	time.sleep(0.025)
	print("*****start up sequence complete*****")

def calculate_crc(data):
    CRC = 0xFF
    for BitIndex in range(31, 7, -1):
        BitValue = (data >> BitIndex) & 0x01
        CRC = crc8(BitValue, CRC)
    CRC = ~CRC & 0xFF
    return CRC

def crc8(BitValue, CRC):
    Temp = CRC & 0x80
    if BitValue == 0x01:
        Temp ^= 0x80
    CRC <<= 1
    if Temp > 0:
        CRC ^= 0x1D
    return CRC

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

try: 	
	start_up()
	time.sleep(1)
	while True:
		# data = 0x040000F7
		# print("CrC:", hex(calculate_crc(data)))
		print("whoami:", whoami())
		print("bank:", xfer(READ_CURR_BANK))
		print("bank:", xfer(READ_BANK_LSB))
		time.sleep(1)
	
except KeyboardInterrupt:
	spi.close()
