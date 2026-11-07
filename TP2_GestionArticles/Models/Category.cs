using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;

namespace TP2_GestionArticles.Models
{
    public class Category
    {
        public int CategoryId { get; set; }

        [Required]
        [Display(Name = "Nom")]
        public string CategoryName { get; set; }

        public ICollection<Product>? Products { get; set; }
    }
}