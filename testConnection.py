import serial #type: ignore
import serial.tools.list_ports #type: ignore
import time
import sys

def list_available_ports():
    """List all available COM ports and their descriptions"""
    print("=== Available COM Ports ===")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("No COM ports detected. Check if your device is connected.")
        return []
    
    for i, port in enumerate(ports):
        print(f"{i+1}. {port.device}: {port.description}")
    
    return ports

def test_connection(port_name, baud_rates=[9600, 115200, 250000, 500000]):
    """Try to connect to a specific port with different baud rates"""
    print(f"\n=== Testing connection to {port_name} ===")
    
    for baud in baud_rates:
        print(f"Trying baud rate: {baud}...")
        try:
            # Attempt connection with a short timeout
            ser = serial.Serial(port_name, baud, timeout=2)
            print(f"SUCCESS! Connected to {port_name} at {baud} baud rate.")
            
            # Try to read/write as a further test
            try:
                ser.write(b'\n')  # Send a newline character
                time.sleep(0.5)
                response = ser.read(10)  # Try to read a response
                if response:
                    print(f"Device responded with: {response}")
            except Exception as e:
                print(f"Note: Could connect but had read/write error: {e}")
            
            # Close and return successful connection info
            ser.close()
            return port_name, baud
            
        except serial.SerialException as e:
            print(f"Failed: {e}")
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            
        print("---")
    
    print(f"Could not connect to {port_name} with any of the tried baud rates.")
    return None, None

def main():
    print("=== Arduino Serial Connection Diagnostic Tool ===\n")
    
    # Step 1: List available ports
    ports = list_available_ports()
    if not ports:
        return
    
    # Step 2: Try to connect to each port
    successful_connection = False
    
    for port in ports:
        port_name, baud = test_connection(port.device)
        if port_name:
            successful_connection = True
            print(f"\n=== SOLUTION ===")
            print(f"Use these settings in your script:")
            print(f"ser = serial.Serial('{port_name}', {baud}, timeout=5)")
            break
    
    if not successful_connection:
        print("\n=== TROUBLESHOOTING STEPS ===")
        print("1. Disconnect and reconnect your Arduino")
        print("2. Try a different USB cable")
        print("3. Try a different USB port on your computer")
        print("4. Check if Arduino needs drivers installed")
        print("5. Verify the Arduino is programmed correctly and the serial monitor in Arduino IDE works")
        print("6. Restart your computer")
        print("7. Check for Windows Device Manager errors (yellow exclamation marks)")

if __name__ == "__main__":
    main()
    print("\nPress Enter to exit...")
    input()