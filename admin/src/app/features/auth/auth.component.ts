import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="card" style="max-width: 420px; margin: 0 auto;">
      <h2>Admin Sign In</h2>
      <form (ngSubmit)="login()">
        <label>Email</label>
        <input class="input" [(ngModel)]="email" name="email" type="email" required />
        <label>Password</label>
        <input class="input" [(ngModel)]="password" name="password" type="password" required />
        <button class="btn" type="submit" style="margin-top: 10px;">Sign In</button>
      </form>
    </div>
  `
})
export class AuthComponent {
  email = '';
  password = '';

  constructor(private auth: AuthService, private router: Router) {}

  login() {
    this.auth.login(this.email, this.password).subscribe(tokens => {
      this.auth.saveTokens(tokens);
      this.router.navigate(['/admin']);
    });
  }
}
