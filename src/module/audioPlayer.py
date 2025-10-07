import time
import os
import pygame

class CommandAudioPlayer:
    def __init__(self, audio_folder):
        self.audio_folder = os.path.abspath(audio_folder)
        self.last_command = None
        self.command_start_time = None
        self.is_playing = False
        pygame.mixer.init()

    def _play_audio(self, audio_path):
        self.is_playing = True
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        return True
    

    def process_command(self,command):
        #if there is not nothing to resolve, break
        if command is None:
            return
    
        print(f"processed command: {command}")
        now = time.time()        
        ## if the system is playing, we let it go until it finish completely.
        if self.is_playing and command != "SALUDA":
            self.is_playing = pygame.mixer.music.get_busy()
            return  
        ## if the command is the same, reboot the counter.
        if command != self.last_command:
            self.last_command = command
            self.command_start_time = now
            return
        # if the command different to the last, remains X second(s) is validated.
        if now - self.command_start_time >= 1  and command != "NO GESTURE":
            # if the command is specific, stop playing.
            if command == 'SALUDA':
                self.is_playing = False
                self.last_command = None
                self.command_start_time = None
                pygame.mixer.music.stop()
                return
            # otherwise, swapp the audio.
            audio_path = os.path.join(self.audio_folder, f"{command}.mp3")
            print(f"playing record: {audio_path}")
            if os.path.exists(audio_path):
                value = self._play_audio(audio_path)  
                self.is_playing = value                
            self.last_command = None
            self.command_start_time = None
