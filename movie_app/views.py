from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.shortcuts import render
from .rdf_handler import RDFDataHandler
from django.contrib.auth import authenticate, login, logout

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .models import MovieClick


# Python imports
import datetime
import random

# Models
from django.contrib.auth.models import User
from .models import Movie, Genre, Comments, Profile

# Forms
from movie_app.forms import CommentForm, UserSignUpForm, UserLoginForm, ChangeUserPasswordForm, DeleteAccountForm, ProfileUpdateForm


# Views
from django.shortcuts import render
from .rdf_handler import RDFDataHandler

def homepage(request):
    if request.user.is_authenticated:
        # Si el usuario está logueado, obtener recomendaciones personalizadas
        recommended_movies = recommend_movies_for_user(request.user)
    else:
        # Si no está logueado, no mostrar recomendaciones
        recommended_movies = []

    # Ruta al archivo RDF
    rdf_file = "movie.rdf"
    rdf_handler = RDFDataHandler(rdf_file)
    
    # Consulta SPARQL para obtener películas
    query = """
    PREFIX ns0: <http://example.org/movies/>
    SELECT ?title ?release_date ?poster WHERE {
        ?movie ns0:title ?title . 
        ?movie ns0:release_date ?release_date . 
        ?movie ns0:poster ?poster .
    } ORDER BY DESC(?release_date) LIMIT 100
    """
    results = rdf_handler.execute_query(query)

    # Convertir resultados a una lista de diccionarios
    movies = [
        {"title": str(row["title"]), "release_date": str(row["release_date"]), "poster": str(row["poster"])}
        for row in results
    ]

    context = {
        "popular_movies": movies,
        "latest_movies": movies,
        "recommended_movies": recommended_movies,  # Se pasan las recomendaciones
    }
    return render(request, "movie_app/homepage.html", context)

# def homepage(request):
#     today = datetime.datetime.now().strftime("%Y-%m-%d")
#     popular_movies = Movie.objects.order_by('-popularity').filter(is_active=True)[:6] # Most popular 6 Movies
#     latest_movies = Movie.objects.order_by('-release_date').filter(is_active=True, release_date__range=("2004-01-01", today))
#     paginator = Paginator(latest_movies, 20)
#     page_number = request.GET.get("page")
#     last_movies = paginator.get_page(page_number,)
#     context = dict(popular_movies=popular_movies, last_movies=last_movies)
#     return render(request, 'movie_app/homepage.html', context=context)
        
def most_popular_movies_view(request):
    popular_movies = Movie.objects.order_by('-popularity').filter(is_active=True)[:10]
    paginator = Paginator(popular_movies, 20)
    page_number = request.GET.get("page")
    p_movies = paginator.get_page(page_number)
    page_title = f"Welcome, {request.user.username}"
    
    context = {
        'popular_movies': p_movies,
        'page_title': page_title,
    }
    return render(request, 'movie_app/most-popular-movies.html', context=context)


def category_view(request, category_slug):
    category = get_object_or_404(Genre,slug=category_slug, is_active=True)
    category_movies = Movie.objects.filter(genre=category)
    paginator = Paginator(category_movies,20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = dict(category=category,category_movies=page_obj, page_title=category.title )
    return render(request, 'movie_app/category-detail.html', context=context)


# Movie Detail

def movie_detail_view(request, movie_slug):
    movie = get_object_or_404(Movie,slug=movie_slug, is_active=True)
    form = CommentForm(request.POST or None)
    if request.user.is_authenticated:
        form.fields['user'].queryset = User.objects.filter(username=request.user.username)
    movie_comments = Comments.objects.filter(movie=movie)
    paginator = Paginator(movie_comments, 10)
    page_number = request.GET.get('page')
    paginated_page = paginator.get_page(page_number)
    context = dict(movie=movie, form=form, movie_comments=paginated_page)
    if form.is_valid():
        form = form.save(commit=False)
        form.user = request.user
        form.movie = movie
        form.save()
        messages.success(request, 'Your comment was successfully recorded')
        return redirect(reverse('movie_app:movie_detail_view', args=(movie.slug,)))
    return render(request, 'movie_app/movie-detail.html', context=context)


# Search ##

def search(request):    
    search_term = request.GET.get('search')
    movie_items = Movie.objects.filter(title__icontains=search_term)
    paginator = Paginator(movie_items,20)
    page_number = request.GET.get('page')
    obj = paginator.get_page(page_number)
    context = dict(search_movies=obj, search_term=search_term)
    return render(request, 'search.html', context=context)


# Authentication

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, f"Welcome {request.user.get_full_name()} You Already Logged in.")
        return redirect('/')
    form = UserLoginForm(request.POST or None)
    context = dict(form=form, page_title='Login')
    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'{request.user.username} You are succesfully logged in.')
            return redirect('/')
        messages.warning(request, 'Wrong password or username. Please check the info and try again.')
        return render(request, 'registration/authentication.html', context=context)
    return render(request, 'registration/authentication.html', context=context)

# Signup
def signup_View(request):
    form = UserSignUpForm(request.POST or None)
    context = dict(form=form, page_title='Signup')
    if form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data.get('password'))
        user.save()
        Profile.objects.create(user=user)
        messages.success(request, 'Your Account/Profile is Succesfully Created.')
        return redirect(reverse('movie_app:login'))
    return render(request, 'registration/authentication.html', context)

# logout
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request,'You are logged out.')
        return redirect('/')
    else:
        if request.META.get('HTTP_REFERER'):
            return redirect(request.META['HTTP_REFERER'])
        else:
            return redirect('/')


# Change Password
@login_required(login_url='/login/')
def change_password_view(request):
        user = request.user
        form = ChangeUserPasswordForm(request.POST or None)
        if form.is_valid():
            password = form.cleaned_data.get('old_password')
            new_password = form.cleaned_data['new_password']
            if user.check_password(password): # this can be done in forms.py form validation but i prefer to make it on view level.
                user.set_password(new_password) # hashing string password data.
                user.save()
                messages.success(request, f'{user.username} your password changed succesfully.')
                return redirect(user.profile.get_absolute_url())
            messages.warning(request, 'Password is wrong. Please check and try again.')
            return redirect(reverse('movie_app:change_password'))
    
        context = dict(form=form, page_title=f'{user.username} Change Password')
        return render(request, 'registration/authentication.html', context=context)


# Delete Account
@login_required(login_url='/login/')
def delete_account_view(request):
    form = DeleteAccountForm(request.POST or None)
    if form.is_valid():
        if form.cleaned_data['number'] == request.session.get('confirmation_int'):
            user = request.user
            user.delete()
            messages.success(request, 'Your account has been deleted :(')
            return redirect('movie_app:signup')
        messages.warning(request, 'Wrong confirmation number. Please check and try again.')
        return redirect('movie_app:delete_account_view')
    confirmation_int = random.randint(1000000,15000000)
    request.session['confirmation_int'] = confirmation_int
    context = dict(form=form, confirmation_int=confirmation_int, page_title=f'{request.user.username} Account Delete')
    return render(request, 'registration/delete.html', context=context)

# PROFILE

# profile detail
def profile_detail_view(request, profile_slug):
    profile = get_object_or_404(Profile, slug=profile_slug, is_active=True)
    user_comments = profile.user.comments_set.all()
    paginator = Paginator(user_comments,10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = dict(profile=profile, user_comments=page_obj)
    return render(request, 'movie_app/profile-detail.html', context=context )

# change profile info
@login_required(login_url='/login/')
def update_profile_view(request):
    profile = get_object_or_404(Profile, user=request.user, is_active=True)
    form = ProfileUpdateForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your Profile Succesfully Updated')
        return redirect(profile.get_absolute_url())
    context = dict(form=form, page_title = f'{request.user.username} Profile Update')
    return render(request, 'registration/authentication.html', context=context)

def recommend_movies_for_user(user):
    # Obtener las películas más clicadas por el usuario, con la cantidad de clics
    user_interactions = MovieClick.objects.filter(user=user).values('movie').annotate(num_clicks=Count('movie')).order_by('-num_clicks')

    if not user_interactions:
        return []  # Si no hay interacciones, no hay recomendaciones

    # Obtener los IDs de las películas más clicadas
    movie_ids = [interaction['movie'] for interaction in user_interactions]

    # Si se tienen IDs de películas, obtener las películas correspondientes
    if movie_ids:
        recommended_movies = Movie.objects.filter(id__in=movie_ids).order_by('-release_date')[:10]  # Top 10 más recientes
        return recommended_movies
    return []  # Si no se encuentran películas, devolver una lista vacía


# Ejemplo de cómo registrar un clic de película
def movie_click_view(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    if request.user.is_authenticated:
        print(f"User {request.user.username} clicked on {movie.title}")
        MovieClick.objects.create(user=request.user, movie=movie)
        messages.success(request, "Your click was registered!")
    else:
        print("User is not authenticated")

    return redirect('movie_app:movie_detail_view', movie_slug=movie.slug)
