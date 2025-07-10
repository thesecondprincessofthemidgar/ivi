from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse

def login_view(request):
    from django.contrib.auth import authenticate, login
    
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("polls:index"))
        else:
            return render(request, "login.html", {"error_message": "Invalid login."})
    else:
        # Render the login form
        return render(request, "login.html")
    
def logout_view(request):
    from django.contrib.auth import logout
    
    logout(request)
    return redirect("polls:index")  # Redirect to the index page of the polls app