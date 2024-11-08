import can
import threading
import time
import os

CAN_DEVICE_ID = 0x0DA
CAN_CHANNEL = 'can0'
BITRATE = 100000

def setup_virtual_can():
    """
    Sets up a virtual CAN interface (can0).
    This function is for Linux systems and requires root privileges.
    Run the following commands manually if this does not work:
    sudo modprobe vcan
    sudo ip link add dev can0 type vcan
    sudo ip link set up can0
    """
    os.system("sudo modprobe vcan")
    os.system("sudo ip link add dev can0 type vcan")
    os.system("sudo ip link set up can0")

def send_specific_can_message(message_id, data):
    """Send a specific CAN message based on user input."""
    try:
        bus = can.interface.Bus(channel=CAN_CHANNEL, bustype='socketcan', bitrate=BITRATE)
        message = can.Message(arbitration_id=message_id, data=data, is_extended_id=False)

        bus.send(message)
        print(f"Sent CAN message: ID={hex(message.arbitration_id)}, Data={message.data}")
    except can.CanError as e:
        print(f"Failed to send CAN message: {e}")
    except Exception as e:
        print(f"Error sending CAN message: {e}")

def countdown_sender():
    """Send CAN messages in a countdown from 60 minutes (3600 seconds)."""
    total_seconds = 3600

    try:
        bus = can.interface.Bus(channel=CAN_CHANNEL, bustype='socketcan', bitrate=BITRATE)

        while total_seconds >= 0:
            time_hi = (total_seconds >> 8) & 0xFF
            time_lo = total_seconds & 0xFF
            data = [0x0C, 0x01, time_hi, time_lo, 0x00, 0x00, 0x00, 0x00]

            message = can.Message(arbitration_id=CAN_DEVICE_ID, data=data, is_extended_id=False)
            
            try:
                bus.send(message)
                print(f"Sent CAN countdown message: ID={hex(message.arbitration_id)}, Data={message.data}")
            except can.CanError as e:
                print(f"Failed to send CAN message: {e}")

            time.sleep(1)
            total_seconds -= 1

        print("Countdown completed.")
    except Exception as e:
        print(f"Error in countdown sender: {e}")

def interactive_mode():
    """Function to handle user input and send messages accordingly."""
    while True:
        user_input = input("Press 1-4 to send Messages or 'q' to quit: ").strip()
        
        if user_input == '1':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)
        
        elif user_input == '2':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)
     
        elif user_input == '3':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)

        elif user_input == '4':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)    
        
        if user_input == '5':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)
        
        elif user_input == '6':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)
     
        elif user_input == '7':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)

        elif user_input == '8':
            message_id = 0x0DA
            data = [0x04, 0x01, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00]
            send_specific_can_message(message_id, data)    

        elif user_input.lower() == 'q':
            print("Exiting interactive mode.")
            break
        
        else:
            print("Invalid input. Please press '1-9' or 'q'.")

def receive_can_messages():
    """Function to receive CAN messages and print them."""
    try:
        bus = can.interface.Bus(channel=CAN_CHANNEL, interface='socketcan', bitrate=BITRATE)

        while True:
            message = bus.recv(timeout=1.0)
            if message:
                print(f"Received CAN message: ID={hex(message.arbitration_id)}, Data={message.data}")
    except Exception as e:
        print(f"Error receiving CAN messages: {e}")

if __name__ == "__main__":
    setup_virtual_can()

    # Start receiving CAN messages in a separate thread
    # receiver_thread = threading.Thread(target=receive_can_messages, daemon=True)
    # receiver_thread.start()

    try:
        interactive_mode()
    except KeyboardInterrupt:
        print("\nStopped CAN message simulation.")
