from django.shortcuts import render, redirect
from .models import Room, Message
from django.contrib import messages

def index(request):
    if request.method == 'POST':
        username = request.POST['username']
        room = request.POST['room']

        # check if room already exists
        if Room.objects.filter(room_name=room).exists():
            return redirect('room', room_name=room, username=username)
        else:
            # create new room if it doesn't exist
            new_room = Room.objects.create(room_name=room)
            new_room.save()
            return redirect('room', room_name=room, username=username)
    return render(request, 'chat/index.html')

def room(request, room_name, username):
    room = Room.objects.get(room_name=room_name)
    messages = Message.objects.filter(room=room)
    return render(request, 'chat/message.html', {
        'room_name': room_name,
        'user': username,
        'messages': messages
    })